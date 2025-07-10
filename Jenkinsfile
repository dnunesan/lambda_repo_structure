pipeline {
    agent any

    environment {
        // Define aquí variables que usarás a lo largo del pipeline
        // Por ejemplo, el nombre de tu función Lambda y el nombre de tu S3 bucket
        LAMBDA_FUNCTION_NAME = 'miFuncionLambdaEjemplo'
        S3_BUCKET_NAME = 'tu-bucket-para-lambda-artifacts-12345' // ¡Cámbialo por un nombre único!
        LAMBDA_HANDLER = 'main.handler' // Si tu archivo es main.py y la función es handler
        LAMBDA_RUNTIME = 'python3.9' // O el runtime que uses
        LAMBDA_DESCRIPTION = 'Mi primera función Lambda desplegada con Jenkins'
    }

    stages {
        // --- Etapa 1: Validación de Credenciales AWS (ya la tienes y funciona) ---
        stage('Validate AWS Credentials') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS-DEFAULT-REGION', variable: 'AWS_REGION'),
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                        export PATH=$PATH:/home/jenkins/.local/bin
                        echo "=== Validación de Credenciales AWS ==="
                        echo "Región configurada: $AWS_REGION"
                        echo "AWS CLI versión: $(aws --version)"
                        echo ""
                        echo "🔍 Probando autenticación..."
                        aws sts get-caller-identity
                        if [ $? -eq 0 ]; then
                            echo ""
                            echo "✅ Credenciales AWS válidas"
                            echo ""
                        else
                            echo ""
                            echo "❌ ERROR: Fallo al validar las credenciales AWS."
                            exit 1
                        fi
                    '''
                }
            }
        }

        // --- Etapa 2: Empaquetar Código Lambda ---
        stage('Package Lambda Code') {
            steps {
                script {
                    // Asegúrate de que este directorio contenga tu código Lambda
                    // Por ejemplo, 'src/lambda_function/'
                    def lambdaSourceDir = 'lambda_function'
                    def zipFileName = "${env.LAMBDA_FUNCTION_NAME}.zip"

                    // Limpia cualquier artefacto previo
                    sh "rm -f ${zipFileName}"

                    // Navega al directorio fuente de la Lambda, zipea el contenido y vuelve al directorio base
                    sh """
                        echo "Empaquetando ${lambdaSourceDir} en ${zipFileName}..."
                        cd ${lambdaSourceDir}
                        zip -r ../${zipFileName} .
                        cd ..
                        echo "✅ Código Lambda empaquetado exitosamente."
                    """
                    env.LAMBDA_ZIP_FILE = zipFileName // Guarda el nombre del zip en una variable de entorno
                }
            }
        }

        // --- Etapa 3: Desplegar Lambda en AWS ---
        stage('Deploy Lambda to AWS') {
            steps {
                withCredentials([
                    string(credentialsId: 'AWS-DEFAULT-REGION', variable: 'AWS_REGION'),
                    string(credentialsId: 'AWS_ACCESS_KEY_ID', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'AWS_SECRET_ACCESS_KEY', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                        export PATH=$PATH:/home/jenkins/.local/bin
                        echo "=== Despliegue de Función Lambda ==="
                        echo "Función: $LAMBDA_FUNCTION_NAME"
                        echo "Bucket S3 para artefactos: $S3_BUCKET_NAME"
                        echo "Archivo ZIP: $LAMBDA_ZIP_FILE"

                        # 1. Crear el Bucket S3 si no existe (solo si lo vas a usar para subir el ZIP)
                        # Este paso es idempotente, no falla si el bucket ya existe
                        echo "Verificando/creando bucket S3: $S3_BUCKET_NAME"
                        if ! aws s3api head-bucket --bucket "$S3_BUCKET_NAME" 2>/dev/null; then
                            echo "Bucket $S3_BUCKET_NAME no existe, creándolo..."
                            aws s3api create-bucket --bucket "$S3_BUCKET_NAME" --region "$AWS_REGION"
                            echo "✅ Bucket $S3_BUCKET_NAME creado."
                        else
                            echo "✅ Bucket $S3_BUCKET_NAME ya existe."
                        fi
                        echo ""

                        # 2. Subir el archivo ZIP a S3
                        echo "Subiendo ${LAMBDA_ZIP_FILE} a s3://${S3_BUCKET_NAME}/"
                        aws s3 cp "${LAMBDA_ZIP_FILE}" "s3://${S3_BUCKET_NAME}/${LAMBDA_ZIP_FILE}"
                        echo "✅ Archivo ZIP subido a S3."
                        echo ""

                        # 3. Comprobar si la función Lambda ya existe
                        echo "Comprobando si la función Lambda '$LAMBDA_FUNCTION_NAME' existe..."
                        FUNCTION_EXISTS=$(aws lambda get-function --function-name "$LAMBDA_FUNCTION_NAME" --query 'Configuration.FunctionArn' 2>/dev/null)

                        if [ -z "$FUNCTION_EXISTS" ]; then
                            # La función no existe, crearla
                            echo "Función Lambda '$LAMBDA_FUNCTION_NAME' no existe, creándola..."
                            # NOTA: Necesitarás un ARN de rol de ejecución de Lambda.
                            # Reemplaza 'arn:aws:iam::123456789012:role/mi-rol-ejecucion-lambda' con el ARN de tu rol.
                            # Este rol debe tener permisos para ser asumido por Lambda y ejecutar el código.
                            aws lambda create-function \
                                --function-name "$LAMBDA_FUNCTION_NAME" \
                                --runtime "$LAMBDA_RUNTIME" \
                                --handler "$LAMBDA_HANDLER" \
                                --memory-size 128 \
                                --timeout 30 \
                                --role "arn:aws:iam::123456789012:role/mi-rol-ejecucion-lambda" \
                                --code S3Bucket="${S3_BUCKET_NAME}",S3Key="${LAMBDA_ZIP_FILE}" \
                                --description "$LAMBDA_DESCRIPTION" \
                                --publish
                            echo "✅ Función Lambda '$LAMBDA_FUNCTION_NAME' creada."
                        else
                            # La función ya existe, actualizarla
                            echo "Función Lambda '$LAMBDA_FUNCTION_NAME' ya existe, actualizando código..."
                            aws lambda update-function-code \
                                --function-name "$LAMBDA_FUNCTION_NAME" \
                                --s3-bucket "$S3_BUCKET_NAME" \
                                --s3-key "$LAMBDA_ZIP_FILE" \
                                --publish
                            echo "✅ Código de la función Lambda '$LAMBDA_FUNCTION_NAME' actualizado."

                            echo "Actualizando configuración de la función Lambda '$LAMBDA_FUNCTION_NAME' (si es necesario)..."
                            # Puedes añadir aquí --handler, --runtime, --description, etc. si necesitas actualizarlos
                            # Por ejemplo: aws lambda update-function-configuration --function-name "$LAMBDA_FUNCTION_NAME" --description "$LAMBDA_DESCRIPTION"
                            echo "✅ Configuración de la función Lambda '$LAMBDA_FUNCTION_NAME' verificada/actualizada."
                        fi
                        echo ""
                        echo "🎉 Despliegue de Lambda completado exitosamente."
                    '''
                }
            }
        }
    }
}
