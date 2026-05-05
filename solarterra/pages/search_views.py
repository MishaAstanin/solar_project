from django.shortcuts import render
from load_cdf.models import *
from data_cdf.models import *
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.apps import apps

from pages.forms import SourceForm, PlotForm, ExportForm
import datetime as dt

from pages.plotting import get_plots

def _default_source_initial():
    return {
        "ts_start": dt.datetime(year=2013, month=1, day=1, hour=1),
        "ts_end": dt.datetime(year=2013, month=12, day=30, hour=1),
    }


def _render_sources(request, *, source_form, plot_form, export_form, fresh=False, status=200):
    context = {
        "datasets": Dataset.objects.have_data().order_by("tag"),
        "source_form": source_form,
        "plot_form": plot_form,
        "export_form": export_form,
        "fresh": fresh,
    }
    return render(request, "pages/sources.html", context=context, status=status)


def search(request):

    if request.method != "GET":
        return HttpResponse("Search page expects GET", status=405)

    return _render_sources(
        request,
        source_form=SourceForm(initial=_default_source_initial()),
        plot_form=PlotForm(),
        export_form=ExportForm(),
        fresh=True,
    )

def export(request):
    if request.method != "POST":
        return HttpResponse("Export endpoint expects POST", status=405)

    source_form = SourceForm(data=request.POST)
    plot_form = PlotForm()  # unbound; only for consistent page rendering on invalid export
    export_form = ExportForm(data=request.POST)

    if not (source_form.is_valid() and export_form.is_valid()):
        return _render_sources(
            request,
            source_form=source_form,
            plot_form=plot_form,
            export_form=export_form,
            fresh=False,
            status=400,
        )

    #export_format = export_form.cleaned_data["export_format"]
    sources = source_form.cleaned_data["sources"]
    ts_start = source_form.cleaned_data["ts_start"]
    ts_end = source_form.cleaned_data["ts_end"]

    return HttpResponse('Export stub!', status=200)

def plot(request):
    if request.method != "POST":
        return HttpResponse('Plot endpoint expects POST', status=405)

    source_form = SourceForm(data=request.POST)
    plot_form = PlotForm(data=request.POST)
    export_form = ExportForm()

    if not (source_form.is_valid() and plot_form.is_valid()):
        return _render_sources(
            request,
            source_form=source_form,
            plot_form=plot_form,
            export_form=export_form,
            fresh=False,
            status=400,
        )

    var_instances = Variable.objects.filter(id__in=source_form.cleaned_data['sources'])
    t_start = source_form.cleaned_data['ts_start']
    t_stop = source_form.cleaned_data['ts_end']
    validate = source_form.cleaned_data['validate']
    plots = get_plots(var_instances, t_start, t_stop, validate)
  
    context = {
        't_start' : t_start,
        't_stop' : t_stop,
        'plots' : plots,

    }
    return render(request, "pages/plot_page.html", context=context)
