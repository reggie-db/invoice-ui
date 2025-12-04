"""Vaadin Grid Dash component package."""

import json
import os as _os

from dash.development.base_component import Component, _explicitize_args

_this_module = _os.path.dirname(__file__)

_js_dist = [
    {
        "relative_package_path": "vaadin_grid.min.js",
        "namespace": "vaadin_grid",
    }
]

_css_dist = []


class VaadinGrid(Component):
    """A VaadinGrid component with lazy loading via dataProvider.

    Keyword arguments:

    - id (string; optional):
        The ID used to identify this component in Dash callbacks.

    - columns (list of dicts; optional):
        Array of column definitions with 'path' and optional 'header'.

    - pageItems (dict; optional):
        Page data returned from server: {page, items}.

    - totalCount (number; optional):
        Total count of items for pagination.

    - requestedPage (number; optional):
        Currently requested page (set by grid on scroll).

    - requestedPageSize (number; optional):
        Currently requested page size.
    """

    _children_props = []
    _base_nodes = ["children"]
    _namespace = "vaadin_grid"
    _type = "VaadinGrid"

    @_explicitize_args
    def __init__(
        self,
        id=Component.UNDEFINED,
        columns=Component.UNDEFINED,
        pageItems=Component.UNDEFINED,
        totalCount=Component.UNDEFINED,
        requestedPage=Component.UNDEFINED,
        requestedPageSize=Component.UNDEFINED,
        **kwargs,
    ):
        self._prop_names = [
            "id",
            "columns",
            "pageItems",
            "totalCount",
            "requestedPage",
            "requestedPageSize",
        ]
        self._valid_wildcard_attributes = []
        self.available_properties = self._prop_names
        self.available_wildcard_properties = []
        _explicit_args = kwargs.pop("_explicit_args")
        _locals = locals()
        _locals.update(kwargs)
        args = {k: _locals[k] for k in _explicit_args if k != "children"}

        super(VaadinGrid, self).__init__(**args)


__all__ = ["VaadinGrid"]
