const path = require("path");
const TerserPlugin = require("terser-webpack-plugin");

const dashLibraryName = "vaadin_grid";

module.exports = {
  entry: { main: "./src/lib/index.js" },
  output: {
    path: path.resolve(__dirname, dashLibraryName),
    filename: `${dashLibraryName}.min.js`,
    library: dashLibraryName,
    libraryTarget: "window",
  },
  // Don't externalize React - Vaadin needs its own bundled React
  externals: {
    "prop-types": "PropTypes",
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: {
          loader: "babel-loader",
          options: {
            presets: ["@babel/preset-env", "@babel/preset-react"],
            plugins: ["@babel/plugin-proposal-object-rest-spread"],
          },
        },
      },
      {
        test: /\.css$/,
        use: ["style-loader", "css-loader"],
      },
    ],
  },
  resolve: {
    extensions: [".js", ".jsx"],
  },
  optimization: {
    minimizer: [
      new TerserPlugin({
        extractComments: false,
      }),
    ],
  },
};
