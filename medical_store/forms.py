from django import forms
from .models import StoreProduct, StoreBatch, StoreRequest, StoreRequestItem


class ProductForm(forms.ModelForm):
    allowed_units = forms.MultipleChoiceField(
        choices=StoreProduct.UNIT_CHOICES,
        required=True,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "unit-check"}),
        label="Allowed Units",
    )
    pack_pieces = forms.IntegerField(required=False, min_value=1, label="Pack contains how many pieces?", widget=forms.NumberInput(attrs={"class": "form-control"}))
    carton_pieces = forms.IntegerField(required=False, min_value=1, label="Carton contains how many pieces?", widget=forms.NumberInput(attrs={"class": "form-control"}))
    set_pieces = forms.IntegerField(required=False, min_value=1, label="Set contains how many pieces?", widget=forms.NumberInput(attrs={"class": "form-control"}))

    class Meta:
        model = StoreProduct
        fields = ["name", "code", "manufacturer", "category", "shelf", "minimum_stock", "is_active"]
        widgets = {field: forms.TextInput(attrs={"class": "form-control"}) for field in ["name", "code", "manufacturer", "category", "shelf"]}
        widgets.update({
            "minimum_stock": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shelf"].required = True
        if self.instance and self.instance.pk:
            self.fields["allowed_units"].initial = self.instance.get_allowed_units()
            pieces = self.instance.unit_pieces or {}
            self.fields["pack_pieces"].initial = pieces.get("Pack")
            self.fields["carton_pieces"].initial = pieces.get("Carton")
            self.fields["set_pieces"].initial = pieces.get("Set")

    def clean(self):
        cleaned = super().clean()
        units = cleaned.get("allowed_units") or []
        for unit, field in [("Pack", "pack_pieces"), ("Carton", "carton_pieces"), ("Set", "set_pieces")]:
            if unit in units and not cleaned.get(field):
                self.add_error(field, f"Please enter how many pieces are inside the {unit}.")
        return cleaned

    def save(self, commit=True):
        product = super().save(commit=False)
        units = self.cleaned_data.get("allowed_units") or ["Piece"]
        product.allowed_units = units
        product.unit = units[0]
        product.unit_pieces = {
            "Pack": self.cleaned_data.get("pack_pieces") or 1,
            "Carton": self.cleaned_data.get("carton_pieces") or 1,
            "Set": self.cleaned_data.get("set_pieces") or 1,
        }
        if commit:
            product.save()
        return product


class ReceiveStockForm(forms.ModelForm):
    received_unit = forms.ChoiceField(choices=StoreProduct.UNIT_CHOICES, widget=forms.Select(attrs={"class": "form-select"}))

    class Meta:
        model = StoreBatch
        fields = ["product", "supplier_name", "batch_number", "received_date", "manufacturing_date", "expiry_date", "received_quantity", "received_unit", "notes"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select", "id": "id_product"}),
            "supplier_name": forms.TextInput(attrs={"class": "form-control"}),
            "batch_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional"}),
            "received_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "manufacturing_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "expiry_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "received_quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["batch_number"].required = False
        self.fields["manufacturing_date"].required = True
        self.fields["expiry_date"].required = True

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        unit = cleaned.get("received_unit")
        if product and unit and unit not in product.get_allowed_units():
            self.add_error("received_unit", "This unit is not allowed for the selected product.")
        return cleaned


class StoreRequestForm(forms.ModelForm):
    class Meta:
        model = StoreRequest
        fields = ["reason"]
        widgets = {
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Reason for request"}),
        }


class StoreRequestItemForm(forms.ModelForm):
    class Meta:
        model = StoreRequestItem
        fields = ["product", "requested_quantity", "requested_unit"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "requested_quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "requested_unit": forms.Select(attrs={"class": "form-select"}),
        }
