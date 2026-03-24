const React = require('react');

function SyntaxHighlighter({ children }) {
  return React.createElement('pre', { 'data-testid': 'syntax-highlighter' }, children);
}

module.exports = {
  Prism: SyntaxHighlighter,
  default: SyntaxHighlighter,
  vscDarkPlus: {},
};
