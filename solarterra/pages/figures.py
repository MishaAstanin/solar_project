import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np


def scatter(plot):

    if len(plot.y_arrays) == 0 or len(plot.y_arrays[0]) == 0:
        return '<div class="no_data">No significant data for this period.</div>'

    fig = go.Figure()

    x, y = plot.get_values(0)

    fig.add_trace(go.Scatter(
        x=x, y=y, connectgaps=False, mode="lines+markers"))

    fig.update_traces(connectgaps=False, marker=dict(size=4))
    fig.update_layout(
        xaxis_range=[plot.t_start, plot.t_stop],
        yaxis_title=plot.variable.get_axis_label(),
    )


    fig.update_yaxes(type=plot.variable.scaletyp)

    config = {'displayModeBar': False}

    plot_div = fig.to_html(config=config, full_html=False,
                           div_id=f"plot_div_{plot.variable.id}", default_width="100%")
    return plot_div


def n_trace(plot):

    fields = plot.y_fields
    
    if len(plot.y_arrays) == 0:
        return '<div class="no_data">No significant data for this period.</div>'

    fig = make_subplots(rows=len(fields), cols=1,
                        shared_xaxes=True, vertical_spacing=0.05)
    for index, field in enumerate(fields):
        x, y = plot.get_values(index)
        fig.add_trace(go.Scatter(
            x=plot.x_field_array,
            y=plot.y_arrays[index],
            connectgaps=False,
            mode="lines+markers",
        ),
            row=index + 1,
            col=1
        )
        fig['layout'][f"yaxis{index+1}"]['title'] = plot.variable.get_axis_label(index)
        fig['layout'][f"xaxis{index+1}"]['range'] = [plot.t_start, plot.t_stop]

    fig.update_traces(marker=dict(size=4))
    

    fig.update_layout(
        height=700,
        #xaxis_range=[ts[0], ts[1]],
        showlegend=False,
    )

    config = {'displayModeBar': False}
    plot_div = fig.to_html(config=config, full_html=False,
                           div_id=f"plot_div_{plot.variable.id}", default_width="100%")

    return plot_div

def spectrogram(plot):
    if plot.z_matrix is None or plot.z_matrix.size == 0:
        return '<div class="no_data">No significant data for this period.</div>'

    if np.all(np.isnan(plot.z_matrix)):
        return '<div class="no_data">No significant data for this period (all values are NaN).</div>'

    z_data = plot.z_matrix.T.copy()

    data_scaletyp = getattr(plot.variable, 'scaletyp', None)

    try:
        axis_label = plot.variable.get_axis_label()
    except Exception:
        axis_label = None

    if not axis_label:
        axis_label = plot.variable.name

    if data_scaletyp == 'log':
        with np.errstate(divide='ignore', invalid='ignore'):
            z_data = np.log10(z_data)
        z_data[~np.isfinite(z_data)] = np.nan
        colorbar_title = f"log₁₀({axis_label})"
    else:
        colorbar_title = axis_label

    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        x=plot.x_axis,
        y=plot.y_axis,
        z=z_data,
        colorscale='Jet',
        colorbar=dict(title=colorbar_title),
        hoverongaps=False,
    ))

    fig.update_layout(
        xaxis_title='Time',
        yaxis_title=plot.y_axis_label,
        xaxis_range=[plot.t_start, plot.t_stop],
        height=500,
    )

    if plot.y_scaletyp == 'log':
        fig.update_yaxes(type='log')

    config = {'displayModeBar': False}
    plot_div = fig.to_html(
        config=config,
        full_html=False,
        div_id=f"plot_div_{plot.variable.id}",
        default_width="100%"
    )
    return plot_div