pipeline {
    agent any

    parameters {
        string(name: 'DOCKERHUB_USERNAME', defaultValue: 'knightprime007', description: 'Docker Hub Namespace')
        string(name: 'IMAGE_NAME', defaultValue: 'business-crm-lead-api', description: 'Docker Image Repository Name')
        string(name: 'OCI_HOST', defaultValue: 'crm.vaikuntrix.in', description: 'Target Public Hostname')
    }

    environment {
        GIT_SHA = "${env.GIT_COMMIT ? env.GIT_COMMIT.take(7) : error('GIT_COMMIT is missing; immutable Git SHA tag is required')}"
        IMAGE_FULL_TAG = "${params.DOCKERHUB_USERNAME}/${params.IMAGE_NAME}:${env.GIT_SHA}"
        IMAGE_LATEST_TAG = "${params.DOCKERHUB_USERNAME}/${params.IMAGE_NAME}:latest"
        DOCKERHUB_CRED_ID = 'docker-hub-credentials'
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
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

        stage('Build ARM64 Image') {
            steps {
                script {
                    echo "Building ARM64 Docker image (linux/arm64): ${IMAGE_FULL_TAG}..."
                    sh "docker buildx build --platform linux/arm64 -t ${IMAGE_FULL_TAG} -t ${IMAGE_LATEST_TAG} --load ."
                }
            }
        }

        stage('Container Security Scan') {
            steps {
                script {
                    echo "Scanning ARM64 container image ${IMAGE_FULL_TAG} with Trivy..."
                    sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --severity HIGH,CRITICAL --exit-code 1 ${IMAGE_FULL_TAG}"
                }
            }
        }

        stage('Push Docker Hub') {
            steps {
                script {
                    echo "Pushing container image ${IMAGE_FULL_TAG} and ${IMAGE_LATEST_TAG} to Docker Hub..."
                    withCredentials([usernamePassword(credentialsId: DOCKERHUB_CRED_ID, usernameVariable: 'DH_USER', passwordVariable: 'DH_PASS')]) {
                        sh 'echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin'
                        sh "docker push ${IMAGE_FULL_TAG}"
                        sh "docker push ${IMAGE_LATEST_TAG}"
                    }
                }
            }
        }

        stage('Deploy OCI') {
            steps {
                script {
                    echo "Deploying P02 image ${IMAGE_FULL_TAG} to OCI host..."
                    sh """
                        if [ ! -f /opt/projects/business-crm/.env ]; then
                            echo "ERROR: Production environment file /opt/projects/business-crm/.env not found on OCI host!"
                            exit 1
                        fi
                        cp docker-compose.yml /opt/projects/business-crm/docker-compose.yml
                        P02_IMAGE="${IMAGE_FULL_TAG}" docker compose --env-file /opt/projects/business-crm/.env -f /opt/projects/business-crm/docker-compose.yml pull
                        P02_IMAGE="${IMAGE_FULL_TAG}" docker compose --env-file /opt/projects/business-crm/.env -f /opt/projects/business-crm/docker-compose.yml up -d
                    """
                }
            }
        }

        stage('Post-Deployment Verification') {
            steps {
                script {
                    sh """
                        MAX_ATTEMPTS=15
                        SLEEP_SECONDS=2
                        CURL_TIMEOUT=2
                        HEALTH_URL="http://127.0.0.1:8001/health"
                        DOCS_URL="http://127.0.0.1:8001/docs"

                        echo "Layer 1 Verification: Bounded readiness check for internal application health (\$HEALTH_URL)..."

                        ATTEMPT=1
                        SUCCESS=0

                        while [ \$ATTEMPT -le \$MAX_ATTEMPTS ]; do
                            HTTP_CODE=\$(curl -s -o /dev/null -w "%{http_code}" --max-time "\$CURL_TIMEOUT" "\$HEALTH_URL") || HTTP_CODE="000"

                            if [ "\$HTTP_CODE" = "200" ]; then
                                echo "[Attempt \$ATTEMPT/\$MAX_ATTEMPTS] Layer 1 Healthcheck: PASS (HTTP 200 OK)"
                                SUCCESS=1
                                break
                            else
                                echo "[Attempt \$ATTEMPT/\$MAX_ATTEMPTS] Application starting up (HTTP \$HTTP_CODE). Retrying..."
                                if [ "\$ATTEMPT" -lt "\$MAX_ATTEMPTS" ]; then
                                    sleep "\$SLEEP_SECONDS"
                                fi
                                ATTEMPT=\$((ATTEMPT + 1))
                            fi
                        done

                        if [ \$SUCCESS -ne 1 ]; then
                            echo "ERROR: Layer 1 application readiness failed after \$MAX_ATTEMPTS attempts against \$HEALTH_URL (Final HTTP status: \$HTTP_CODE)!"
                            exit 1
                        fi

                        echo "Layer 1 Verification: Internal API documentation (\$DOCS_URL)..."
                        curl --fail --silent --show-error --max-time 10 "\$DOCS_URL" > /dev/null

                        echo "Layer 1 Verification: Verifying running container image tag corresponds to ${IMAGE_FULL_TAG}..."
                        RUNNING_IMAGE=\$(docker inspect --format '{{.Config.Image}}' business_crm_lead_api 2>/dev/null || echo "NOT_RUNNING")
                        if [ "\$RUNNING_IMAGE" != "${IMAGE_FULL_TAG}" ]; then
                            echo "ERROR: Running container image (\$RUNNING_IMAGE) does not match deployed image ${IMAGE_FULL_TAG}!"
                            exit 1
                        fi
                        echo "Running container verified: \$RUNNING_IMAGE"
                    """

                    echo "Layer 2 Verification: Cloudflared Tunnel status..."
                    sh '''
                        if pgrep cloudflared >/dev/null || systemctl is-active cloudflared >/dev/null 2>&1 || docker ps | grep -q cloudflared; then
                            echo "Cloudflared tunnel status: RUNNING"
                        else
                            echo "ERROR: Cloudflared tunnel process is not detected on host!"
                            exit 1
                        fi
                    '''

                    echo "Layer 3 Verification: Public domain (https://${params.OCI_HOST}/health)..."
                    sh """
                        HTTP_STATUS=\$(curl -o /dev/null -s -w "%{http_code}" --max-time 10 https://${params.OCI_HOST}/health || echo "CURL_ERROR")
                        if [ "\$HTTP_STATUS" = "200" ]; then
                            echo "Public Cloudflare route: PASS (HTTP 200 OK)"
                        else
                            echo "ERROR: Public Cloudflare route failed with status \$HTTP_STATUS (Expected HTTP 200)"
                            exit 1
                        fi
                    """
                }
            }
        }

        stage('OCI Disk Cleanup') {
            steps {
                script {
                    echo "Performing targeted disk space cleanup for obsolete P02 images..."
                    sh """
                        docker image prune -f
                        docker container prune -f
                        docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}}' | grep '${params.DOCKERHUB_USERNAME}/${params.IMAGE_NAME}' | grep -v '${env.GIT_SHA}' | grep -v 'latest' | awk '{print \$2}' | xargs -r docker rmi -f || true
                    """
                }
            }
        }
    }

    post {
        always {
            cleanWs(deleteDirs: true, notFailBuild: true)
        }
        success {
            echo "Successfully built, tested, scanned, published, and deployed P02 commit ${env.GIT_SHA}!"
        }
        failure {
            echo "Pipeline failed! Deployment aborted on commit ${env.GIT_COMMIT}."
        }
    }
}
