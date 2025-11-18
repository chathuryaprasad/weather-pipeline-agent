"""Database schema definitions for improved structure."""
from typing import List, Tuple

# Cities table schema
CITIES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `cities` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(255) NOT NULL UNIQUE,
  `country` VARCHAR(100),
  `country_code` VARCHAR(10),
  `latitude` DECIMAL(10, 8),
  `longitude` DECIMAL(11, 8),
  `timezone` VARCHAR(50),
  `population` INT,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_name` (`name`),
  INDEX `idx_country` (`country`),
  INDEX `idx_location` (`latitude`, `longitude`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Weather observations table schema (improved)
WEATHER_OBSERVATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `weather_observations` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `city_id` INT,
  `city_name` VARCHAR(255) NOT NULL,
  `timestamp` DATETIME NOT NULL,
  `temperature` DECIMAL(5, 2),
  `feels_like` DECIMAL(5, 2),
  `pressure` INT,
  `humidity` TINYINT UNSIGNED,
  `wind_speed` DECIMAL(5, 2),
  `wind_deg` SMALLINT,
  `wind_gust` DECIMAL(5, 2),
  `condition` VARCHAR(255),
  `condition_code` VARCHAR(50),
  `visibility` INT,
  `cloudiness` TINYINT UNSIGNED,
  `uv_index` DECIMAL(4, 2),
  `raw` JSON,
  `source` VARCHAR(50) DEFAULT 'openweathermap',
  `ingestion_job_id` VARCHAR(100),
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `unique_city_timestamp` (`city_name`, `timestamp`),
  INDEX `idx_city_id` (`city_id`),
  INDEX `idx_city_name` (`city_name`),
  INDEX `idx_timestamp` (`timestamp`),
  INDEX `idx_city_timestamp` (`city_name`, `timestamp`),
  INDEX `idx_ingestion_job` (`ingestion_job_id`),
  FOREIGN KEY (`city_id`) REFERENCES `cities`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

# Ingestion logs table schema
INGESTION_LOGS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `ingestion_logs` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `job_id` VARCHAR(100) NOT NULL UNIQUE,
  `job_type` VARCHAR(50) NOT NULL,
  `status` VARCHAR(20) NOT NULL,
  `started_at` DATETIME NOT NULL,
  `completed_at` DATETIME,
  `duration_seconds` INT,
  `cities_processed` INT DEFAULT 0,
  `records_inserted` INT DEFAULT 0,
  `records_updated` INT DEFAULT 0,
  `records_failed` INT DEFAULT 0,
  `error_message` TEXT,
  `metadata` JSON,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_job_id` (`job_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_job_type` (`job_type`),
  INDEX `idx_started_at` (`started_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

def get_all_schema_sql() -> List[str]:
    """Return all schema creation SQL statements in order."""
    return [
        CITIES_TABLE_SQL,
        WEATHER_OBSERVATIONS_TABLE_SQL,
        INGESTION_LOGS_TABLE_SQL
    ]



