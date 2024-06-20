
from django import forms
from .models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'file']
class SearchForm(forms.Form):
    query = forms.CharField(label='Search Query')