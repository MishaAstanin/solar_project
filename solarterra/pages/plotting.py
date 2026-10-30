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
        # queryset evaluation
        query.set_arrays()
        row_count = query.get_array_len() or 0 
                
        if row_count > 0:
            print(f"[PERF] DB query {item.dataset.tag}: {time.time()-t_q:.2f}s, rows: {row_count}")
            aggregation = row_count > Bin.PPP
        else:
            aggregation = False

        if aggregation and row_count > 0:
            _i_start = tf(t_start)
            _i_stop = tf(t_end)
            _bin_starts = np.arange(
                _i_start,
                _i_stop + (bin_instance.bin_seconds * 2),
                step=bin_instance.bin_seconds)
            _bin_centers = _bin_starts + bin_instance.half_bin
            query.set_bin_map(_bin_starts)
            
        # need to generate plot spaces, even if there is not data for a plot
        for var in vars_in_query:
            plot = Plot(
                    t_start=t_start,
                    t_stop=t_end,
                    variable=var,
                    x_field=filter_field,
                    validate=validate)
            
            # no computations if there isn`t any data
            if row_count > 0:

                if aggregation:
                    plot.bin_instance = bin_instance
                    plot.bin_starts_array = _bin_starts
                    plot.bin_centers_array = _bin_centers
            
                plot.aggregation = aggregation
                t_p = time.time()
                plot.set_arrays(query)

            # get the plotly figure
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
