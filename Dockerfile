FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY pom.xml .
RUN mvn -B dependency:go-offline
COPY src src
COPY lib lib
COPY public public
COPY drizzle drizzle
RUN mvn -B package
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /build/target/donation-system.jar /app/donation-system.jar
ENV DATA_DIR=/data PORT=8080
EXPOSE 8080
CMD ["java", "-XX:MaxRAMPercentage=70", "-jar", "/app/donation-system.jar"]
