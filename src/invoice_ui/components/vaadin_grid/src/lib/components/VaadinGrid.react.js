import PropTypes from "prop-types";

// Only import Vaadin once to prevent "dom-module already defined" error
let BundledReact, BundledReactDOM, Grid, GridSortColumn;

if (!window.__vaadinGridInitialized) {
  window.__vaadinGridInitialized = true;
  BundledReact = require("react");
  BundledReactDOM = require("react-dom/client");
  const vaadin = require("@vaadin/react-components");
  Grid = vaadin.Grid;
  GridSortColumn = vaadin.GridSortColumn;

  window.__vaadinGridModules = { BundledReact, BundledReactDOM, Grid, GridSortColumn };
} else {
  ({ BundledReact, BundledReactDOM, Grid, GridSortColumn } = window.__vaadinGridModules);
}

/**
 * VaadinGrid is a Dash component that wraps the Vaadin React Grid.
 * Uses dataProvider for true lazy loading.
 */
const VaadinGridComponent = (props) => {
  const { id, columns, pageItems, totalCount, setProps } = props;
  const React = window.React;

  const containerRef = React.useRef(null);
  const rootRef = React.useRef(null);
  const pendingCallbacks = React.useRef(new Map());

  // Handle incoming page data
  React.useEffect(() => {
    if (pageItems && pageItems.page !== undefined) {
      const callback = pendingCallbacks.current.get(pageItems.page);
      if (callback) {
        callback(pageItems.items, totalCount || 0);
        pendingCallbacks.current.delete(pageItems.page);
      }
    }
  }, [pageItems, totalCount]);

  React.useEffect(() => {
    if (containerRef.current && !rootRef.current) {
      rootRef.current = BundledReactDOM.createRoot(containerRef.current);
    }

    if (rootRef.current) {
      // Create dataProvider for lazy loading
      const dataProvider = (params, callback) => {
        const page = params.page;
        const size = params.pageSize;

        // Store callback to be called when data arrives
        pendingCallbacks.current.set(page, callback);

        // Request data from Dash
        if (setProps) {
          setProps({
            requestedPage: page,
            requestedPageSize: size
          });
        }
      };

      const gridElement = BundledReact.createElement(
        Grid,
        {
          dataProvider: dataProvider,
          pageSize: 50,
          theme: "row-stripes",
        },
        (columns || []).map((col) =>
          BundledReact.createElement(GridSortColumn, {
            key: col.path,
            path: col.path,
            header: col.header || col.path,
            autoWidth: true,
          })
        )
      );

      rootRef.current.render(gridElement);
    }
  }, [columns, setProps]);

  // Update grid when new data arrives
  React.useEffect(() => {
    // Grid will automatically call dataProvider callback
  }, [pageItems]);

  React.useEffect(() => {
    return () => {
      if (rootRef.current) {
        rootRef.current.unmount();
        rootRef.current = null;
      }
    };
  }, []);

  return React.createElement("div", {
    id: id,
    ref: containerRef,
    style: { minHeight: "400px" },
  });
};

VaadinGridComponent.propTypes = {
  /** The ID used to identify this component in Dash callbacks. */
  id: PropTypes.string,
  /** Array of column definitions with 'path' and optional 'header'. */
  columns: PropTypes.arrayOf(
    PropTypes.shape({
      path: PropTypes.string.isRequired,
      header: PropTypes.string,
    })
  ),
  /** Page data returned from server: {page, items}. */
  pageItems: PropTypes.shape({
    page: PropTypes.number,
    items: PropTypes.arrayOf(PropTypes.object),
  }),
  /** Total count of items. */
  totalCount: PropTypes.number,
  /** Currently requested page (set by grid). */
  requestedPage: PropTypes.number,
  /** Currently requested page size (set by grid). */
  requestedPageSize: PropTypes.number,
  /** Dash-assigned callback for property changes. */
  setProps: PropTypes.func,
};

export default VaadinGridComponent;
