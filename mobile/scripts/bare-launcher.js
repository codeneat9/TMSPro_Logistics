const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const command = process.argv[2] || 'start';
const root = path.resolve(__dirname, '..');
const hasIos = fs.existsSync(path.join(root, 'ios'));
const hasAndroid = fs.existsSync(path.join(root, 'android'));

const commandMap = {
  start: ['react-native', ['start']],
  ios: ['react-native', ['run-ios']],
  android: ['react-native', ['run-android']],
};

const selected = commandMap[command];
if (!selected) {
  console.error(`Unknown command: ${command}`);
  process.exit(1);
}

if (!hasIos || !hasAndroid) {
  console.error('Bare workflow not initialized yet.');
  console.error('Generate native folders first using STEP8_BARE_WORKFLOW_KICKOFF.md.');
  process.exit(1);
}

const [bin, args] = selected;
const result = spawnSync('npx', [bin, ...args], {
  cwd: root,
  stdio: 'inherit',
  shell: true,
});

process.exit(result.status || 0);
