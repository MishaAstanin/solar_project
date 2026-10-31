from load_cdf.models import *
from solarterra.utils import ts_float_resolver as tf
from solarterra.utils import float_ts_resolver as ft

import math
import datetime as dt
from django.db import connection
from pages.figures import scatter, n_trace, spectrogram
import logging


logger = logging.getLogger('solarterra.plot')


class DBQuery():

    def __init__(self, dataset, filter_field, t_start, t_stop, fields):

        # instance
        self.dataset = dataset
        # class
        self.data_class = dataset.dynamic.resolve_class()

        # time strings
        self.start_limit = tf(t_start)
        self.stop_limit = tf(t_stop)

        # field (instance) on which the filtering happens
        self.filter_field = filter_field
        self.fields = fields
        # 0th position of the filter_field is important
        self.all_fields = [filter_field] + fields

        # not evaluated queryset
        self.queryset = None
        # transposed and sorted arrays of values
        self.arrays = None

        # bin mapping over over the array of epochs
        self.bin_map = None

        # True когда данные уже агрегированы в SQL
        self.sql_aggregated = False


    def query(self):
        kwargs = {
            f'{self.filter_field}__gte': self.start_limit,
            f'{self.filter_field}__lte': self.stop_limit,
        }
        self.queryset = self.data_class.objects.filter(**kwargs).order_by(self.filter_field)
    
    # alternative way ?
    """
    def evaluate(self):sorted_pile = pile[pile[:, 0].argsort()]
        # no memory cache
        rows = self.queryset.values_list(*self.all_fields).iterator()
        # here is where slow evaluation happens
        arrays = [np.array(col) for col in zip(*rows)]
        self.named_arrays = dict(zip(fields, arrays))
    """

    def set_arrays(self):
        rows = list(self.queryset.values_list(*self.all_fields))
        if not rows:
            return

        columns = list(zip(*rows))

        self.arrays = [
            np.array(column, dtype=object)
            if any(isinstance(value, (list, tuple)) for value in column if value is not None)
            else np.array(column)
            for column in columns
        ]

    def get_array_len(self):
        if self.arrays is not None:
            return self.arrays[0].shape[0]

    def get_full_time_array(self):
        if self.arrays is not None:
            return self.arrays[0]

    def set_bin_map(self, bin_starts_array):
        self.bin_map = np.searchsorted(bin_starts_array, self.get_full_time_array(), side="right")

    def set_arrays_sql_aggregated(self, bin_seconds, i_start, field_validators):
        """
        Агрегация на стороне PostgreSQL через GROUP BY.
        Вместо загрузки миллионов строк в Python, БД сама считает среднее
        по бинам и возвращает ~1000 строк.

        Результат (self.arrays) имеет тот же формат, что и set_arrays():
        - self.arrays[0] — временное поле (bin centers)
        - self.arrays[1..] — агрегированные значения
        - ArrayField сохраняются как object-массив из list

        field_validators: dict {field_name: (validmin, validmax)}
          validmin/validmax — скаляр, list или None.
          Для list — валидация покомпонентная (для ArrayField).
        """
        table = self.data_class._meta.db_table

        # Убираем дубликаты из all_fields, сохраняя порядок.
        # Дубликаты бывают, когда несколько переменных ссылаются
        # на одно и то же поле БД.
        unique_fields = list(dict.fromkeys(self.all_fields))

        # Определяем, какие поля — массивы, а какие — скаляры.
        # Берём одну строку из БД (LIMIT 1) и смотрим типы.
        sample = self.queryset.values_list(*unique_fields).first()
        if sample is None:
            return

        field_info = {}  # field_name → (is_array, size)
        for field_name, value in zip(unique_fields, sample):
            if isinstance(value, (list, tuple)):
                field_info[field_name] = (True, len(value))
            else:
                field_info[field_name] = (False, 1)

        # --- Строим SQL-запрос ---
        #
        # Бин: FLOOR((epoch - i_start) / bin_seconds) + 1
        # +1 чтобы совпасть с np.searchsorted(..., side="right") в set_bin_map.
        #
        # Валидация: AVG(CASE WHEN field BETWEEN vmin AND vmax THEN field END)
        # AVG() в PostgreSQL игнорирует NULL — невалидные точки исключаются
        # ДО усреднения, как в оригинальном Python-коде.

        select_parts = [
            f'FLOOR(("{self.filter_field}" - %s) / %s)::int + 1 AS bin_idx'
        ]
        params = [i_start, bin_seconds]

        # col_map: field_name → [(column_index_in_result, component_or_None), ...]
        col_map = {}
        result_col = 1  # 0 — bin_idx

        for field_name in unique_fields:
            is_array, size = field_info[field_name]
            validmin, validmax = field_validators.get(field_name, (None, None))

            if is_array:
                col_map[field_name] = []
                for comp in range(size):
                    access = f'("{field_name}")[{comp + 1}]'  # PG массивы 1-based
                    vmin = self._pick_validator(validmin, comp)
                    vmax = self._pick_validator(validmax, comp)
                    expr = self._build_avg_expr(access, vmin, vmax, params)
                    select_parts.append(f'{expr} AS avg_{field_name}_{comp}')
                    col_map[field_name].append((result_col, comp))
                    result_col += 1
            else:
                access = f'"{field_name}"'
                vmin = self._pick_validator(validmin, None)
                vmax = self._pick_validator(validmax, None)
                expr = self._build_avg_expr(access, vmin, vmax, params)
                select_parts.append(f'{expr} AS avg_{field_name}')
                col_map[field_name] = [(result_col, None)]
                result_col += 1

        sql = f"""
            SELECT {', '.join(select_parts)}
            FROM "{table}"
            WHERE "{self.filter_field}" >= %s
              AND "{self.filter_field}" <= %s
            GROUP BY bin_idx
            ORDER BY bin_idx
        """
        params.extend([self.start_limit, self.stop_limit])

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        if not rows:
            self.sql_aggregated = True
            return

        # Размер результата совпадает с bin_starts_array в Plot.prepare_bins().
        n_bins = len(np.arange(
            i_start,
            self.stop_limit + bin_seconds * 2,
            step=bin_seconds
        ))

        # --- Собираем массивы из SQL-результата ---
        unique_arrays = {}

        for field_name in unique_fields:
            is_array, size = field_info[field_name]

            if is_array:
                arr = np.empty(n_bins, dtype=object)
                for i in range(n_bins):
                    arr[i] = [np.nan] * size

                for row in rows:
                    bin_idx = row[0]
                    if bin_idx < 0 or bin_idx >= n_bins:
                        continue
                    components = []
                    for col_idx, _ in col_map[field_name]:
                        val = row[col_idx]
                        components.append(float(val) if val is not None else np.nan)
                    arr[bin_idx] = components

                unique_arrays[field_name] = arr
            else:
                arr = np.full(n_bins, np.nan, dtype=float)
                col_idx = col_map[field_name][0][0]
                for row in rows:
                    bin_idx = row[0]
                    if 0 <= bin_idx < n_bins:
                        val = row[col_idx]
                        if val is not None:
                            arr[bin_idx] = float(val)
                unique_arrays[field_name] = arr

        # Разворачиваем в исходный порядок all_fields (с дубликатами)
        self.arrays = [unique_arrays[fn] for fn in self.all_fields]
        self.sql_aggregated = True

    @staticmethod
    def _pick_validator(validator, component_index):
        """Выбирает validmin/validmax для компоненты или скаляра."""
        if validator is None:
            return None
        if isinstance(validator, list):
            if component_index is None or component_index >= len(validator):
                return None
            return validator[component_index]
        return validator

    @staticmethod
    def _build_avg_expr(access, vmin, vmax, params):
        """Строит AVG(...) с опциональной SQL-валидацией через CASE WHEN."""
        conditions = []
        if vmin is not None:
            try:
                conditions.append(f'{access} >= %s')
                params.append(float(vmin))
            except (ValueError, TypeError):
                pass
        if vmax is not None:
            try:
                conditions.append(f'{access} <= %s')
                params.append(float(vmax))
            except (ValueError, TypeError):
                pass
        if conditions:
            return f'AVG(CASE WHEN {" AND ".join(conditions)} THEN {access} END)'
        return f'AVG({access})'


class Bin():

    # points per plot: since plot aggregation is dynamic, either need to have fixed bin sizes or points per plot
    PPP = 1000

    def __init__(self, t_start, t_stop):

        timedelta = t_stop - t_start 
        self.bin_seconds = math.ceil(timedelta.total_seconds() / self.PPP)
        self.bin_td = dt.timedelta(seconds=self.bin_seconds)
        self.half_bin = math.ceil(self.bin_seconds / 2)

    def t_next(self, t_current):
        return t_current + self.bin_td

    def t_previous(self, t_current):
        return t_current - self.bin_td


class Plot():

    # start and stop as datetimes
    t_start = None
    t_stop = None
    
    # in seconds
    bin_instance = None
    # numpy range of the starts of time bins
    bin_starts_array = None
    bin_centers_array = None

    # plotly figure
    figure = None

    def __init__(self, t_start, t_stop, variable, x_field, validate):

        # start and stop as datetimes
        self.t_start = t_start
        self.t_stop = t_stop

        # instances of var
        self.variable = variable
      
        # Flag to show if validation will be applied
        self.validate = validate

        # Flag to now if aggregation happened
        self.aggregation = None

        # block for aggregation
        self.bin_instance = None
        # numpy range of the starts of time bins
        self.bin_starts_array = None
        self.bin_centers_array = None

        # name of x_field
        self.x_field = x_field
        # array of timestamps for plot points
        self.x_field_array = None

        # numpy datatype
        self.y_field_numpy_type = variable.get_numpy_data_type()

        dynamic_field = variable.dynamic.first()
        if dynamic_field is None:
            raise ValueError(f"Dynamic field for variable '{variable.name}' not found")

        self.y_db_field = dynamic_field.field_name

        if variable.dims == 1 and variable.dim_sizes is not None:
            dim_sizes = variable.dim_sizes

            if dim_sizes == 1:
                self.component_indexes = [None]
            else:
                if isinstance(dim_sizes, (list, tuple)):
                    total = int(np.prod(dim_sizes))
                else:
                    total = int(dim_sizes)
                self.component_indexes = list(range(total))
        else:
            self.component_indexes = [None]

        self.y_fields = [self.y_db_field] * len(self.component_indexes)

        self.y_arrays = []
        
        self.invalid_values = []
        
        self.figure = None


    @staticmethod
    def _extract_array_component(array_column, component_index):
        result = []

        for row in array_column:
            if row is None or len(row) <= component_index:
                result.append(np.nan)
                continue

            value = row[component_index]
            result.append(np.nan if value is None else value)

        return np.array(result, dtype=float)


    def _get_full_value_array(self, query, component_index):
        field_index = query.all_fields.index(self.y_db_field)
        full_value_array = query.arrays[field_index]

        if component_index is None:
            return full_value_array.astype(self.y_field_numpy_type)

        return self._extract_array_component(full_value_array, component_index)


    def prepare_bins(self, bin_instance):
        i_start = tf(self.t_start)
        i_stop = tf(self.t_stop)
        self.bin_instance = bin_instance
        # *2 here because right limit in arange is non-inclusive, 
        # but a little data in the query could be left beyond last bin, since bin size is rounded
        self.bin_starts_array = np.arange(
                i_start,
                i_stop + (bin_instance.bin_seconds*2),
                step=bin_instance.bin_seconds)
        self.bin_centers_array = self.bin_starts_array + bin_instance.half_bin
    
    # index that marks values beyond validmin - valimax interval
    def validation_index(self, arr, field_index=None):
        if arr is None or len(arr) == 0:
            return None

        condition = False
        
        if self.variable.validmin is not None:
          
            if field_index is not None and isinstance(self.variable.validmin, list):
                validmin = self.variable.validmin[field_index]
            else:
                validmin = self.variable.validmin
            validmin_value = DataType.proper_type(validmin, arr[0])
           
            condition = condition | (arr < validmin_value)

        if self.variable.validmax is not None:
            if field_index is not None and isinstance(self.variable.validmax, list):
                validmax = self.variable.validmax[field_index]
            else:
                validmax = self.variable.validmax
            validmax_value = DataType.proper_type(validmax, arr[0])
           
            condition = condition | (arr > validmax_value)
    
        # can not just swap values here, because for int type there is no nan alternative

        if isinstance(condition, np.ndarray):
            self.invalid_values.append(f"{int(condition.sum())} / {condition.shape[0]} [{validmin}, {validmax}]")
        else:
            condition = None
            self.invalid_values.append("no validmin/validmax")
        
        if self.validate:
            return condition
        else:
            return None


    def get_x_array(self, query):
        self.x_field_array = np.array(list(map(ft, query.get_full_time_array())))

    def get_y_arrays(self, query):
        for component_index in self.component_indexes:
            full_value_array = self._get_full_value_array(query, component_index)

            if np.isnan(full_value_array).all():
                self.y_arrays.append([])
            else:
                self.y_arrays.append(full_value_array)

        # applying validation index in case of no aggregation is a little harder:
        # the only way to skip values when plotting is skipping index in both x_array and y_array at the same index
        # but there is a single x array and y arrays could have different validation indexes so i have to have multiple x_arrays or apply aggregation when plotting
        # chose the second option

    def get_agg_x_array(self):
        self.x_field_array = np.array(list(map(ft, self.bin_centers_array)))

    # definitely could reduce # of steps here
    def get_agg_y_arrays(self, query):
        for i, component_index in enumerate(self.component_indexes):
            full_value_array = self._get_full_value_array(query, component_index)

            # getting an index of nans in value array
            mask = ~np.isnan(full_value_array)

            # getting an index of invalid values
            validation_index = self.validation_index(full_value_array, field_index=i)
            if validation_index is not None and validation_index.any():
                mask = mask & ~validation_index

            # getting maps for only non-nans
            val_bin_map = query.bin_map[mask]
            # getting only non-nans
            val_array = full_value_array[mask]

            idx, pos, counts = np.unique(val_bin_map, return_index=True, return_counts=True)

            # if no aggregation groups survived - no points on the plot
            if idx.shape[0] == 0:
                logger.debug(f"no data in field {self.y_db_field}, out of {self.variable.name} {self.variable.dataset}")
                self.y_arrays.append([])
                continue

            # getting sums for groups
            sums = np.add.reduceat(val_array, pos, axis=0)
            means = sums / counts

            result = np.full(self.x_field_array.shape, np.nan, dtype=float)
            result[idx] = means
            self.y_arrays.append(result)

    def get_sql_agg_y_arrays(self, query):
        """
        Извлекает y-массивы из данных, уже агрегированных в SQL.
        Данные в query.arrays уже содержат ~1000 точек (средние по бинам
        с применённой валидацией), поэтому ни агрегация, ни валидация
        на Python-уровне не нужны.
        """
        for component_index in self.component_indexes:
            full_value_array = self._get_full_value_array(query, component_index)

            if np.isnan(full_value_array).all():
                self.y_arrays.append([])
                continue

            # Выравниваем по размеру x_field_array (на случай расхождения
            # в 1 элемент из-за округления в arange)
            result = np.full(self.x_field_array.shape, np.nan, dtype=float)
            n = min(len(full_value_array), len(result))
            result[:n] = full_value_array[:n]
            self.y_arrays.append(result)
        
    def set_arrays(self, query):
        if self.aggregation:
            self.get_agg_x_array()
            if query.sql_aggregated:
                # Данные уже агрегированы в SQL — быстрая ветка
                self.get_sql_agg_y_arrays(query)
            else:
                # Данные загружены сырыми — старая ветка
                self.get_agg_y_arrays(query)
        else:
            self.get_x_array(query)
            self.get_y_arrays(query)

    # returns a pair of x_array and y_array for each plot
    def get_values(self, index):
        if self.aggregation:
            return self.x_field_array, self.y_arrays[index]
        else:
            # apply validation here instead:
            validation_index = self.validation_index(self.y_arrays[index], field_index=index)
            if validation_index is not None and validation_index.any():
                return self.x_field_array[~validation_index], self.y_arrays[index][~validation_index]
            else:
                return self.x_field_array, self.y_arrays[index]
    


    def get_figure(self):
    
        if len(self.y_fields) == 1:
            self.figure = scatter(self)
        else:
            self.figure = n_trace(self)


class SpectrogramPlot():

    def __init__(self, t_start, t_stop, variable, validate):
        self.t_start = t_start
        self.t_stop = t_stop
        self.variable = variable
        self.validate = validate

        self.x_axis = None

        self.y_axis = None
        self.y_axis_label = None
        self.y_scaletyp = None

        # z_matrix[i][j] value at time i for energy j
        self.z_matrix = None

        self.aggregation = False
        self.invalid_values = []
        self.figure = None

        self.bin_instance = None
    
    def load_data(self):
        dataset = self.variable.dataset
        data_class = dataset.dynamic.resolve_class()

        if data_class is None:
            return

        # time field from depend_0
        if not self.variable.depend_0:
            return

        try:
            depend_0_var = dataset.variables.get(name=self.variable.depend_0)
            filter_field = depend_0_var.dynamic.first().field_name
        except Exception:
            return

        # spectrogram data field
        data_field = self.variable.dynamic.filter(is_array_field=True).first()
        if data_field is None:
            return

        i_start = tf(self.t_start)
        i_stop = tf(self.t_stop)

        qs = data_class.objects.filter(**{
            f'{filter_field}__gte': i_start,
            f'{filter_field}__lte': i_stop,
            f'{data_field.field_name}__isnull': False,
        }).order_by(filter_field).values_list(filter_field, data_field.field_name)

        times = []
        values = []
        for t_val, arr_val in qs.iterator():
            times.append(t_val)
            values.append(arr_val)

        if not times:
            return

        time_array = np.array(times)              # (N,)
        z_matrix = np.array(values, dtype=float)  # (N, M)

        self._apply_validation(z_matrix)

        if len(time_array) > Bin.PPP:
            self.bin_instance = Bin(self.t_start, self.t_stop)
            time_array, z_matrix = self._aggregate(time_array, z_matrix)
            self.aggregation = True

        self.x_axis = np.array(list(map(ft, time_array)))
        self.z_matrix = z_matrix

        # energies from depend_1
        if self.variable.depend_1:
            self._load_energy_axis(dataset, data_class)
        else:
            self.y_axis = np.arange(z_matrix.shape[1], dtype=float)
            self.y_scaletyp = None
    
    def _load_energy_axis(self, dataset, data_class):
        try:
            energy_var = dataset.variables.get(name=self.variable.depend_1)

            if energy_var.is_nrv():
                nrv_entry = dataset.nrv_data.filter(variable=energy_var).first()
                if nrv_entry is None or nrv_entry.value is None:
                    raise ValueError(f"NRV entry for '{energy_var.name}' not found")
                
                self.y_axis = np.array(nrv_entry.value, dtype=float)
                try:
                    self.y_axis_label = energy_var.get_axis_label() or energy_var.name
                except Exception:
                    self.y_axis_label = energy_var.name
                self.y_scaletyp = getattr(energy_var, 'scaletyp', None)
                return
        
            energy_field = energy_var.dynamic.filter(is_array_field=True).first()

            if energy_field is None:
                raise ValueError("Energy variable has no ArrayField")

            energy_values = data_class.objects.filter(
                **{f'{energy_field.field_name}__isnull': False}
            ).values_list(energy_field.field_name, flat=True).first()

            if energy_values:
                self.y_axis = np.array(energy_values, dtype=float)
                try:
                    label = energy_var.get_axis_label()
                    self.y_axis_label = label if label else energy_var.name
                except Exception:
                    self.y_axis_label = energy_var.name
                self.y_scaletyp = getattr(energy_var, 'scaletyp', None)
            else:
                raise ValueError("No energy data found")

        except Exception:
            if self.z_matrix is not None:
                self.y_axis = np.arange(self.z_matrix.shape[1], dtype=float)
            else:
                self.y_axis = np.array([0])
            self.y_scaletyp = None

    def _apply_validation(self, z_matrix):
        if not self.validate or z_matrix is None or z_matrix.size == 0:
            return

        sample = z_matrix.flat[0]
        n_channels = z_matrix.shape[1]

        if self.variable.validmin is not None:
            vmin = self.variable.validmin
            if isinstance(vmin, list):
                vmin_arr = np.array([
                    float(DataType.proper_type(v, sample) or -np.inf)
                    for v in vmin[:n_channels]
                ], dtype=float)
                z_matrix[z_matrix < vmin_arr] = np.nan
            else:
                vmin_val = DataType.proper_type(vmin, sample)
                if vmin_val is not None:
                    z_matrix[z_matrix < float(vmin_val)] = np.nan

        if self.variable.validmax is not None:
            vmax = self.variable.validmax
            if isinstance(vmax, list):
                vmax_arr = np.array([
                    float(DataType.proper_type(v, sample) or np.inf)
                    for v in vmax[:n_channels]
                ], dtype=float)
                z_matrix[z_matrix > vmax_arr] = np.nan
            else:
                vmax_val = DataType.proper_type(vmax, sample)
                if vmax_val is not None:
                    z_matrix[z_matrix > float(vmax_val)] = np.nan

        total = z_matrix.size
        nan_count = int(np.isnan(z_matrix).sum())
        self.invalid_values.append(f"{nan_count} / {total} invalid/missing")

    def _aggregate(self, time_array, z_matrix):
        n = len(time_array)
        bin_size = max(1, n // Bin.PPP)

        starts = np.arange(0, n, bin_size)
        
        counts = np.diff(np.append(starts, n)).astype(float)

        time_sums = np.add.reduceat(time_array.astype(float), starts)
        agg_times = (time_sums / counts).astype(time_array.dtype)

        z_nan_mask = np.isnan(z_matrix)
        z_filled = np.where(z_nan_mask, 0.0, z_matrix)
        z_valid_count = (~z_nan_mask).astype(float)

        z_sums = np.add.reduceat(z_filled, starts, axis=0)
        z_counts = np.add.reduceat(z_valid_count, starts, axis=0)

        z_counts[z_counts == 0] = np.nan
        agg_z = z_sums / z_counts

        return agg_times, agg_z

    def get_figure(self):
        self.figure = spectrogram(self)
