from django import forms
from django.forms.models import BaseInlineFormSet


class AtLeastOneRequiredInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        if not any(cleaned_data and not cleaned_data.get('DELETE', False)
                   for cleaned_data in self.cleaned_data):
            raise forms.ValidationError('Хотя бы один элемент обязателен.')
