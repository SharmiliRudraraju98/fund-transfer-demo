pipeline {
    agent any

    stages {
        stage('Install Account Service Deps') {
            steps {
                dir('account-service') {
                    sh 'pip3 install --break-system-packages -r requirements.txt'
                }
            }
        }

        stage('Install Transfer Service Deps') {
            steps {
                dir('transfer-service') {
                    sh 'pip3 install --break-system-packages -r requirements.txt'
                }
            }
        }

        stage('Install Test Deps') {
            steps {
                sh 'pip3 install --break-system-packages -r requirements-test.txt'
            }
        }

        stage('Syntax Check') {
            steps {
                sh 'python3 -m py_compile account-service/app.py transfer-service/app.py'
            }
        }

        stage('Package') {
            steps {
                sh 'tar -czf fund-transfer-demo.tar.gz account-service transfer-service docker-compose.yml'
                archiveArtifacts artifacts: 'fund-transfer-demo.tar.gz'
            }
        }
    }
}