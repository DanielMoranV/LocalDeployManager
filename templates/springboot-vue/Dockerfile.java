FROM eclipse-temurin:21-jdk-alpine AS builder

# Install Maven
RUN apk add --no-cache maven

WORKDIR /app

# Copy Maven files for dependency caching
COPY backend/pom.xml ./
COPY backend/mvnw ./
COPY backend/.mvn ./.mvn

# Download dependencies (cached layer)
RUN if [ -f mvnw ]; then chmod +x mvnw && ./mvnw dependency:go-offline -B; fi

# Copy source code
COPY backend/src ./src

# Build the application
RUN if [ -f mvnw ]; then \
        ./mvnw clean package -DskipTests -B; \
    else \
        mvn clean package -DskipTests -B; \
    fi

# Production stage
FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

# Install curl for healthchecks
RUN apk add --no-cache curl

# Create app user
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -s /bin/sh -D appuser

# Copy JAR from builder
COPY --from=builder /app/target/*.jar app.jar

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to user
USER appuser

# Expose port
EXPOSE 8080

# JVM options
ENV JAVA_OPTS="-Xmx512m -Xms256m -XX:+UseContainerSupport"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/actuator/health || exit 1

# Run the application
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
