from pages.plot_instances import Bin, DBQuery, Plot, SpectrogramPlot
from solarterra.utils import ts_float_resolver as tf
from load_cdf.models import DynamicField
import numpy as np
import logging


logger = logging.getLogger('solarterra.plot')


def get_plots(variables, t_start, t_end, validate):
    import time
     
    # do the work with the the bin
    Plot.t_start = t_start
    Plot.t_stop = t_end
    bin_instance = Bin(t_start, t_end)
    plots = []

    ts_variables = variables.filter(display_type="time_series")
    spec_variables = variables.filter(display_type="spectrogram")

    for item in ts_variables.order_by('dataset__tag').distinct('dataset__tag', 'depend_0'):
        t_q = time.time()
        vars_in_query = ts_variables.filter(dataset=item.dataset, depend_0=item.depend_0).order_by('name')

        if item.depend_0 is None:
            logger.warning(f"No dependent axis specified for dataset '{item.dataset}', vars '{vars_in_query}'! Skipping")
            continue
        
        filter_field = item.get_depend_field().field_name
        fields = list(DynamicField.objects.filter(variable_instance__in=vars_in_query).values_list('field_name', flat=True))

        query = DBQuery(
                dataset=item.dataset,
                filter_field=filter_field,
                t_start=t_start,
                t_stop=t_end,
                fields=fields)
        
        # creating the query
        query.query()

        # COUNT — быстрый запрос, не загружает данные
        row_count = query.queryset.count()
        aggregation = row_count > Bin.PPP

        if row_count > 0:
            if aggregation:
                # БЫСТРАЯ ВЕТКА: агрегация в SQL (~1000 строк вместо миллионов)
                field_validators = {}
                for var in vars_in_query:
                    dyn = var.dynamic.first()
                    if dyn is None:
                        continue
                    field_validators[dyn.field_name] = (var.validmin, var.validmax)

                query.set_arrays_sql_aggregated(
                    bin_instance.bin_seconds,
                    tf(t_start),
                    field_validators,
                )
                print(f"[PERF] DB query (SQL agg) {item.dataset.tag}: "
                      f"{time.time()-t_q:.2f}s, raw rows: {row_count}")
            else:
                # МЕДЛЕННАЯ ВЕТКА: загрузка всех данных (но их < 1000)
                query.set_arrays()
                print(f"[PERF] DB query {item.dataset.tag}: "
                      f"{time.time()-t_q:.2f}s, rows: {row_count}")
            
        # need to generate plot spaces, even if there is not data for a plot
        for var in vars_in_query:
            plot = Plot(
                    t_start=t_start,
                    t_stop=t_end,
                    variable=var,
                    x_field=filter_field,
                    validate=validate)

            if row_count > 0:
                if aggregation:
                    plot.prepare_bins(bin_instance)
                plot.aggregation = aggregation
                t_p = time.time()
                plot.set_arrays(query)

            plot.get_figure()
            print(f"[PERF] plot {var.name}: {time.time()-t_p:.2f}s")
            plots.append(plot)
    
    for var in spec_variables:
        spec_plot = SpectrogramPlot(
            t_start=t_start,
            t_stop=t_end,
            variable=var,
            validate=validate
        )
        spec_plot.load_data()
        spec_plot.get_figure()
        plots.append(spec_plot)
        
    plots.sort(key=lambda p: (
        p.variable.dataset.tag.lower(),
        p.variable.cdf_order
    ))

    return plots
