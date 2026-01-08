const path = require('path');

module.exports = {
  webpack: {
    alias: {
      '@core': path.resolve(__dirname, 'src'),
    },
  },
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
  jest: {
    configure: {
      transformIgnorePatterns: [
        'node_modules/(?!(axios)/)',
      ],
      moduleNameMapper: {
        '^@core/(.*)$': '<rootDir>/src/$1',
      },
    },
  },
}
