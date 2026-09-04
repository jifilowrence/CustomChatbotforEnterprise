import { spawn } from 'child_process';
import fs from 'fs';

console.log('--- STARTING ENTERPRISE PORTAL DEV LAUNCHER ---');

// Step 1: Initialize Database first
function runInitDb() {
  return new Promise((resolve, reject) => {
    console.log('Running database initialization...');
    const proc = spawn('python3', ['init_db.py'], { stdio: 'inherit' });
    proc.on('close', (code) => {
      if (code === 0) {
        console.log('Database initialized successfully.');
        resolve();
      } else {
        console.error('Database initialization failed. Continuing anyway...');
        resolve(); // Continue to start server even if DB fails initially
      }
    });
  });
}

// Step 2: Start FastAPI and Streamlit
async function launchServers() {
  await runInitDb();

  console.log('Starting FastAPI Backend on port 8000...');
  const fastapi = spawn('python3', ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], {
    stdio: 'inherit'
  });

  console.log('Starting Streamlit Frontend on port 3000...');
  const streamlit = spawn('python3', [
    '-m', 'streamlit', 'run', 'streamlit_app.py',
    '--server.port', '3000',
    '--server.address', '0.0.0.0',
    '--server.enableCORS', 'false',
    '--server.enableXsrfProtection', 'false',
    '--browser.gatherUsageStats', 'false'
  ], {
    stdio: 'inherit'
  });

  // Handle termination signals
  const cleanup = () => {
    console.log('Shutting down servers...');
    fastapi.kill();
    streamlit.kill();
    process.exit(0);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
}

launchServers().catch(err => {
  console.error('Error launching servers:', err);
});
