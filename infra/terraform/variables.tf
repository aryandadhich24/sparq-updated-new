# ============================================================================
# SparqAI — Terraform Variables
# ============================================================================

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "sparqai"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# ---- Networking ----
variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

# ---- Database ----
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "sparqai"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "sparqai_admin"
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

# ---- ECS ----
variable "backend_cpu" {
  description = "Backend task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Backend task memory (MB)"
  type        = number
  default     = 1024
}

variable "frontend_cpu" {
  description = "Frontend task CPU units"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Frontend task memory (MB)"
  type        = number
  default     = 512
}

variable "backend_desired_count" {
  description = "Number of backend tasks"
  type        = number
  default     = 2
}

variable "frontend_desired_count" {
  description = "Number of frontend tasks"
  type        = number
  default     = 2
}

# ---- Domain ----
variable "domain_name" {
  description = "Root domain name (e.g. sparqai.com)"
  type        = string
}

variable "api_subdomain" {
  description = "API subdomain"
  type        = string
  default     = "api"
}

variable "app_subdomain" {
  description = "App subdomain"
  type        = string
  default     = "app"
}

# ---- Secrets ----
variable "secret_key" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "hubspot_client_id" {
  description = "HubSpot OAuth client ID"
  type        = string
  default     = ""
}

variable "hubspot_client_secret" {
  description = "HubSpot OAuth client secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "salesforce_client_id" {
  description = "Salesforce OAuth client ID"
  type        = string
  default     = ""
}

variable "salesforce_client_secret" {
  description = "Salesforce OAuth client secret"
  type        = string
  default     = ""
  sensitive   = true
}

variable "google_api_key" {
  description = "Google Gemini API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "sentry_dsn" {
  description = "Sentry DSN for error tracking"
  type        = string
  default     = ""
}

# ---- DNS / CloudFront ----
variable "create_dns_records" {
  description = "Whether to create Route53 DNS records (requires hosted zone to exist)"
  type        = bool
  default     = false
}
