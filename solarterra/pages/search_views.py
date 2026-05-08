from django.shortcuts import render, redirect
from load_cdf.models import Dataset
from pages.forms import MissionSelectForm, VariableSelectForm
import datetime as dt
from pages.plotting import get_plots


def select_missions(request):
    if request.method == "POST":
        form = MissionSelectForm(request.POST)
        if form.is_valid():
            request.session["selected_missions"] = form.cleaned_data["missions"]
            return redirect("search")
    else:
        form = MissionSelectForm()

    return render(request, "pages/mission_select.html", context={"form": form})

def search(request):
    selected_missions = request.session.get("selected_missions")

    if not selected_missions:
        return redirect("select_missions")

    datasets = (
        Dataset.objects.have_data()
        .filter(mission__in=selected_missions)
        .order_by("mission", "tag")
    )
    
    if request.method == 'POST':
        form = VariableSelectForm(request.POST, missions=selected_missions)
 
        if form.is_valid():
            var_instances = form.cleaned_data['variables']
            t_start = form.cleaned_data['ts_start']
            t_stop = form.cleaned_data['ts_end']
            validate = form.cleaned_data['validate']

            plots = get_plots(var_instances, t_start, t_stop, validate)

            context = {
                't_start' : t_start,
                't_stop' : t_stop,
                'plots' : plots,          
            }
            return render(request, "pages/plot_page.html", context=context)
    else:
        form = VariableSelectForm(
            missions=selected_missions,
            initial={
                'ts_start': dt.datetime(year=2013, month=1, day=1, hour=0),
                'ts_end': dt.datetime(year=2013, month=12, day=30, hour=0),
            }
        )

    return render(request, "pages/variable_select.html", context={
        'datasets': datasets,
        'form': form,
        'selected_missions': selected_missions,
        "has_errors": bool(form.errors),
    })