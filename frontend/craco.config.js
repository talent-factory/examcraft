module.exports = {
  style: {
    postcss: {
      mode: 'extends',
      loaderOptions: (postcssLoaderOptions) => {
        postcssLoaderOptions.postcssOptions.plugins = [
          'tailwindcss',
          'autoprefixer',
        ];
        return postcssLoaderOptions;
      },
    },
  },
}
