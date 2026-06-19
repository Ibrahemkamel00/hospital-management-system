from django import forms
from .models import Location


class NewCSSDRequestForm(forms.Form):
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        label="Location"
    )

    procedure = forms.CharField(
        label="Procedure / Notes",
        required=False,
        max_length=150
    )