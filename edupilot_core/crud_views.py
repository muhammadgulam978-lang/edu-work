from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django import forms
from .crud_config import CRUD_REGISTRY


def get_config_or_404(model_name):
    config = CRUD_REGISTRY.get(model_name)
    if not config:
        raise Http404(f"'{model_name}' is not a registered data model.")
    return config


@login_required
def crud_list_view(request, model_name):
    config = get_config_or_404(model_name)
    Model = config['model']
    list_fields = config.get('list_fields') or [f.name for f in Model._meta.fields[:5]]

    queryset = Model.objects.all().order_by('-id')

    rows = []
    for obj in queryset:
        values = []
        for field_name in list_fields:
            value = getattr(obj, field_name, '')
            # handle choice-field display methods if they exist
            display_method = f'get_{field_name}_display'
            if hasattr(obj, display_method):
                value = getattr(obj, display_method)()
            values.append(value)
        rows.append({'id': obj.id, 'values': values})

    context = {
        'model_name': model_name,
        'label': config['label'],
        'list_fields': list_fields,
        'rows': rows,
        'total_count': queryset.count(),
    }
    return render(request, 'automation/crud_list.html', context)


@login_required
def crud_create_view(request, model_name):
    config = get_config_or_404(model_name)
    Model = config['model']
    FormClass = forms.modelform_factory(Model, fields=config.get('fields', '__all__'))

    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config['label']} record created successfully.")
            return redirect('crud-list', model_name=model_name)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = FormClass()

    context = {
        'model_name': model_name,
        'label': config['label'],
        'form': form,
        'is_edit': False,
    }
    return render(request, 'automation/crud_form.html', context)


@login_required
def crud_update_view(request, model_name, pk):
    config = get_config_or_404(model_name)
    Model = config['model']
    obj = get_object_or_404(Model, pk=pk)
    FormClass = forms.modelform_factory(Model, fields=config.get('fields', '__all__'))

    if request.method == 'POST':
        form = FormClass(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config['label']} record updated successfully.")
            return redirect('crud-list', model_name=model_name)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = FormClass(instance=obj)

    context = {
        'model_name': model_name,
        'label': config['label'],
        'form': form,
        'is_edit': True,
        'obj': obj,
    }
    return render(request, 'automation/crud_form.html', context)


@login_required
def crud_delete_view(request, model_name, pk):
    config = get_config_or_404(model_name)
    Model = config['model']
    obj = get_object_or_404(Model, pk=pk)

    if request.method == 'POST':
        obj.delete()
        messages.success(request, f"{config['label']} record deleted successfully.")
        return redirect('crud-list', model_name=model_name)

    context = {
        'model_name': model_name,
        'label': config['label'],
        'obj': obj,
    }
    return render(request, 'automation/crud_delete_confirm.html', context)