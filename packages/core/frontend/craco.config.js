const path = require('path');

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
  webpack: {
    configure: (webpackConfig) => {
      // Exclude test files and setup files from production build
      webpackConfig.module.rules.push({
        test: /\.(test|spec)\.(ts|tsx|js|jsx)$|setupTests\.(ts|tsx|js|jsx)$/,
        loader: 'ignore-loader',
      });
      return webpackConfig;
    },
  },
  jest: {
    configure: {
      transformIgnorePatterns: [
        'node_modules/(?!(axios)/)',
      ],
    },
  },
}
