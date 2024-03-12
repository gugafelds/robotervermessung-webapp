const withSerwist = require('@serwist/next').default({
  swSrc: 'public/sw.ts',
  swDest: 'public/sw.js',
  disable: process.env.NODE_ENV === 'development',
});

module.exports = withSerwist({
  reactStrictMode: true,
  swcMinify: true,
  compiler: {
    removeConsole: process.env.NODE_ENV !== 'development',
  },
});
