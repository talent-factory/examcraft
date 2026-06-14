const React = require('react');

// Test mock for react-markdown (wired via craco.config.js moduleNameMapper).
// Renders children VERBATIM inside [data-testid="react-markdown"] — it does NOT
// transform Markdown. Tests assert raw Markdown text appears under this testid to
// prove content reached MarkdownRenderer. Do not change the testid or stop passing
// children through unchanged without updating the dependent tests.
function ReactMarkdown({ children }) {
  return React.createElement('div', { 'data-testid': 'react-markdown' }, children);
}

module.exports = ReactMarkdown;
module.exports.default = ReactMarkdown;
