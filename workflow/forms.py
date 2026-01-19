# workflow/forms.py
from django import forms
from .models import Dataset

class DataUploadForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['name', 'file']

class ModelConfigForm(forms.Form):
    MODEL_CHOICES = [
        ('LR',  'SGD: Lojistik Regresyon'),
        ('SVM', 'SGD: Linear SVM'),
        ('PER', 'Perceptron'),
        ('PA',  'PassiveAggressive'),
        ('MLP', 'MLPClassifier'),
    ]
    model = forms.ChoiceField(choices=MODEL_CHOICES)
    learning_rate = forms.FloatField(required=False, initial=0.01)
    batch_size    = forms.IntegerField(required=False, initial=32)
    epochs        = forms.IntegerField(required=False, initial=10)
    test_size     = forms.FloatField(initial=0.2)
    random_state  = forms.IntegerField(initial=42)
