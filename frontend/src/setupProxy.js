// frontend/src/setupProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api', // This tells the proxy to look for any request starting with /api
    createProxyMiddleware({
      target: 'http://127.0.0.1:8000', // This is where Django is running
      changeOrigin: true, // This is important for virtual hosting
    })
  );
};