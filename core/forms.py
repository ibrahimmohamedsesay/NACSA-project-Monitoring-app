from django import forms


class StyledFormMixin:
    """Adds the CSS classes used by the NaCSA interface to every widget."""

    def _style(self):
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check")
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            elif isinstance(w, forms.FileInput):
                w.attrs.setdefault("class", "form-file")
            else:
                w.attrs.setdefault("class", "form-control")
            if isinstance(w, forms.DateInput):
                w.input_type = "date"
                w.format = "%Y-%m-%d"
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault("rows", 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class StyledForm(StyledFormMixin, forms.Form):
    pass


class StyledModelForm(StyledFormMixin, forms.ModelForm):
    pass


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs.setdefault("format", "%Y-%m-%d")
        super().__init__(**kwargs)
