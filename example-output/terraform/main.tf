# Space Fractions — Terraform 1 cloud infrastructure (illustrative).
# Network + containerized microservices + managed data services.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# --- Networking -------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  tags       = { Name = "space-fractions-vpc" }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index}.0/24"
  availability_zone = "${var.region}${count.index == 0 ? "a" : "b"}"
  tags              = { Name = "space-fractions-public-${count.index}" }
}

# --- Data services ----------------------------------------------------------
resource "aws_db_instance" "postgres" {
  identifier     = "space-fractions-postgres"
  engine         = "postgres"
  engine_version = "14"
  instance_class = "db.t3.micro"
  username       = var.db_username
  password       = var.db_password
  allocated_storage = 20
  skip_final_snapshot = true
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id      = "space-fractions-redis"
  engine          = "redis"
  engine_version  = "6.x"
  node_type       = "cache.t3.micro"
  num_cache_nodes = 1
}

resource "aws_elasticsearch_domain" "search" {
  domain_name           = "space-fractions"
  elasticsearch_version = "7.10"

  cluster_config {
    instance_type  = "t3.small.elasticsearch"
    instance_count = 1
  }
}

# --- Container hosting (ECS/Fargate) ----------------------------------------
resource "aws_ecs_cluster" "main" {
  name = "space-fractions"
}

resource "aws_ecs_task_definition" "game" {
  family                   = "space-fractions-game"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  container_definitions = jsonencode([
    {
      name  = "game-component"
      image = var.game_image
      environment = [
        { name = "SERVICE", value = "game-component" },
        { name = "DATABASE_URL", value = "postgres://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/spacefractions" }
      ]
    }
  ])
}
