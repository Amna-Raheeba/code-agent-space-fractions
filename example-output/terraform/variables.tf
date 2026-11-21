variable "region" {
  type        = string
  default     = "us-east-1"
  description = "AWS region to deploy into."
}

variable "db_username" {
  type        = string
  default     = "spacefractions"
  description = "PostgreSQL master username."
}

variable "db_password" {
  type        = string
  default     = "spacefractions"
  sensitive   = true
  description = "PostgreSQL master password."
}

variable "game_image" {
  type        = string
  default     = "space-fractions:latest"
  description = "GameComponent container image."
}
