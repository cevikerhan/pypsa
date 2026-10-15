html,
body,
#root {
  margin: 0;
  min-height: 100%;
  background: #07111f;
  color: #f8fafc;
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

body {
  min-height: 100vh;
}

* {
  box-sizing: border-box;
}

button {
  transition: all 0.2s ease;
}

::-webkit-scrollbar {
  width: 10px;
}

::-webkit-scrollbar-thumb {
  background: rgba(125, 211, 252, 0.18);
  border-radius: 999px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

.MuiTableCell-root {
  border-color: rgba(148, 163, 184, 0.14) !important;
}

.MuiCard-root,
.MuiPaper-root {
  box-shadow: none !important;
}
