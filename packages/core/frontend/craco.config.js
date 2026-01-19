const path = require('path');

module.exports = {
  typescript: {
    enableTypeChecking: false, // Disable TypeScript type checking in webpack
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
  webpack: {
    configure: (webpackConfig) => {
      // Remove ModuleScopePlugin to allow imports from workspace packages
      webpackConfig.resolve.plugins = webpackConfig.resolve.plugins.filter(
        plugin => plugin.constructor.name !== 'ModuleScopePlugin'
      );

      // Disable symlinks to prevent TypeScript from following them
      webpackConfig.resolve.symlinks = false;

      // Add workspace packages to module resolution
      // NOTE: @examcraft/core points to lib (library entry), not src/ directory
      // This prevents conflicts with index.tsx (React app entry point)
      webpackConfig.resolve.alias = {
        ...webpackConfig.resolve.alias,
        '@examcraft/core': path.resolve(__dirname, 'src/lib'),
        '@examcraft/premium': path.resolve(__dirname, '../../premium/frontend/src'),
        '@examcraft/enterprise': path.resolve(__dirname, '../../enterprise/frontend/src'),
      };

      // Configure module resolution to prefer .tsx over .ts for entry points
      // This ensures CRA uses index.tsx (React app) instead of index.ts (library exports)
      webpackConfig.resolve.extensions = [
        '.tsx', '.ts', '.jsx', '.js', '.json', '.wasm', '.mjs'
      ];

      // Include workspace packages in Babel compilation (but not TypeScript checking)
      const oneOfRule = webpackConfig.module.rules.find(rule => rule.oneOf);
      if (oneOfRule) {
        const tsRule = oneOfRule.oneOf.find(
          rule => rule.test && rule.test.toString().includes('tsx')
        );
        if (tsRule) {
          // Extend include to cover workspace packages for Babel transpilation
          tsRule.include = [
            tsRule.include,
            path.resolve(__dirname, '../../premium/frontend/src'),
            path.resolve(__dirname, '../../enterprise/frontend/src'),
          ].filter(Boolean);

          // Disable TypeScript checking for workspace packages
          // TypeScript will only check Core files, Webpack will transpile Premium/Enterprise
          if (tsRule.options && tsRule.options.compilerOptions) {
            tsRule.options.compilerOptions.skipLibCheck = true;
          }
        }
      }

      // Disable TypeScript type checking plugin completely
      // Premium/Enterprise packages have their own tsconfig.json and will be checked separately
      webpackConfig.plugins = webpackConfig.plugins.filter(
        plugin => plugin.constructor.name !== 'ForkTsCheckerWebpackPlugin'
      );

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
