pipeline {
    agent any

    parameters {
        string(name: 'DOCKERHUB_USERNAME', defaultValue: 'knightprime007', description: 'Docker Hub Namespace')
        string(name: 'IMAGE_NAME', defaultValue: 'business-crm-lead-api', description: 'Docker Image Repository Name')
    }

    environment {
        GIT_SHA = "${env.GIT_COMMIT ? env.GIT_COMMIT.take(7) : 'latest'}"
        IMAGE_FULL_TAG = "${params.DOCKERHUB_USERNAME}/${params.IMAGE_NAME}:${env.GIT_SHA}"
        IMAGE_LATEST_TAG = "${params.DOCKERHUB_USERNAME}/${params.IMAGE_NAME}:latest"
    }

    options {
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo "Checked out commit: ${env.GIT_COMMIT}"
            }
        }

        stage('Secret Scan') {
            steps {
                script {
                    echo "Executing Gitleaks secret detection..."
                    sh 'docker run --rm -v "${WORKSPACE}:/source:ro" zricethezav/gitleaks:latest detect --source /source --verbose'
                }
            }
        }

        stage('Test & Coverage') {
            steps {
                script {
                    echo "Running automated test suite with coverage via Python 3.12 container..."
                    sh '''
                        docker run --rm -v "${WORKSPACE}:/app" -w /app python:3.12-slim sh -c "
                            pip install --no-cache-dir -r requirements.txt &&
                            pytest -v --cov=app --cov-report=term-missing
                        "
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    echo "Building hardened multi-stage Docker image: ${IMAGE_FULL_TAG}"
                    sh "docker build -t ${IMAGE_FULL_TAG} -t ${IMAGE_LATEST_TAG} ."
                }
            }
        }

        stage('Container Security Scan') {
            steps {
                script {
                    echo "Scanning container image ${IMAGE_FULL_TAG} with Trivy..."
                    sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --severity HIGH,CRITICAL --exit-code 1 ${IMAGE_FULL_TAG}"
                }
            }
        }

        /*
         * Note: Phase 1 CI scope verifies build, tests, secrets, and container security.
         * Production OCI deployment and Cloudflare tunnel routing are Phase 3 deliverables.
         */
    }

    post {
        always {
            cleanWs(deleteDirs: true, notFailBuild: true)
        }
        success {
            echo "CI Pipeline completed successfully for ${IMAGE_FULL_TAG}."
        }
        failure {
            echo "CI Pipeline failed on commit ${env.GIT_COMMIT}."
        }
    }
}
