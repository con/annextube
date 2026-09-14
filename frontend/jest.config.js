export default {
  preset: 'ts-jest/presets/default-esm',
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/tests/unit'],
  // Jest owns the *.jest.test.ts suites; everything else under tests/unit is
  // Vitest's (it needs the Svelte plugin, see vite.config.ts)
  testMatch: ['**/*.jest.test.ts'],
  extensionsToTreatAsEsm: ['.ts'],
  globals: {
    'ts-jest': {
      useESM: true,
    },
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  transform: {
    '^.+\\.ts$': [
      'ts-jest',
      {
        useESM: true,
      },
    ],
  },
  setupFilesAfterEnv: ['<rootDir>/tests/unit/setup.ts'],
};
