from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse

def health_check(request):
    #returns JsonResponse
    #powered by REST
    return JsonResponse({"status": "ok"})

    