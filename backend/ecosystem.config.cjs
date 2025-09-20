module.exports = {
  apps: [
    {
      name: 'truthlens-api',
      script: 'python3',
      args: 'run.py',
      cwd: '/home/user/webapp/backend',
      env: {
        NODE_ENV: 'development',
        PORT: 8080
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork',
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production',
        PORT: 8080,
        DEBUG: 'false'
      }
    }
  ]
}