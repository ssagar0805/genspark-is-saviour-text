module.exports = {
  apps: [
    {
      name: 'truthlens-frontend',
      script: 'npm',
      args: 'run dev',
      cwd: '/home/user/webapp/frontend',
      env: {
        NODE_ENV: 'development'
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork',
      max_memory_restart: '200M'
    }
  ]
}