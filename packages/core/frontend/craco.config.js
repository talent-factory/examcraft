module.exports = {
  style: {
    postcss: {
      mode: 'extends',
      loaderOptions: (postcssLoaderOptions) => {
        postcssLoaderOptions.postcssOptions.plugins = [
          [
            'tailwindcss',
            {
              config: './tailwind.config.js',
            },
          ],
          'autoprefixer',
        ];
        return postcssLoaderOptions;
      },
    },
  },
}
