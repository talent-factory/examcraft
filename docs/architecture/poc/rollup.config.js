import typescript from '@rollup/plugin-typescript';
import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import { defineConfig } from 'rollup';

export default defineConfig({
  input: {
    index: 'src/index.ts',
    types: 'src/types/index.ts',
    services: 'src/services/index.ts',
    components: 'src/components/index.ts',
    contexts: 'src/contexts/index.ts',
    utils: 'src/utils/index.ts',
  },
  output: [
    {
      dir: 'dist',
      format: 'cjs',
      entryFileNames: '[name].js',
      sourcemap: true,
      exports: 'named',
    },
    {
      dir: 'dist',
      format: 'esm',
      entryFileNames: '[name].esm.js',
      sourcemap: true,
    },
  ],
  external: [
    'react',
    'react-dom',
    'react-router-dom',
    '@tanstack/react-query',
    '@mui/material',
    '@emotion/react',
    '@emotion/styled',
    'axios',
  ],
  plugins: [
    resolve({
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
    }),
    commonjs(),
    typescript({
      tsconfig: './tsconfig.json',
      declaration: true,
      declarationDir: './dist',
      exclude: ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts', '**/*.spec.tsx'],
    }),
  ],
});
