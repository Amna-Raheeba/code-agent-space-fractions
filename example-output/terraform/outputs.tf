output "postgres_endpoint" {
  value       = aws_db_instance.postgres.endpoint
  description = "PostgreSQL 14 endpoint."
}

output "redis_endpoint" {
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
  description = "Redis 6 endpoint."
}

output "elasticsearch_endpoint" {
  value       = aws_elasticsearch_domain.search.endpoint
  description = "Elasticsearch 7 endpoint."
}

output "ecs_cluster" {
  value       = aws_ecs_cluster.main.name
  description = "ECS cluster name."
}
