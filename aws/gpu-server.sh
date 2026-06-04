#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# gpu-server.sh — Start, stop, and check your EC2 GPU backend
#
# Usage:
#   ./aws/gpu-server.sh start    → Start the GPU instance
#   ./aws/gpu-server.sh stop     → Stop it (saves credits)
#   ./aws/gpu-server.sh status   → Check if running + show URL
#   ./aws/gpu-server.sh ssh      → SSH into the instance
#   ./aws/gpu-server.sh logs     → Tail backend logs
#   ./aws/gpu-server.sh deploy   → First-time CloudFormation deploy
# ─────────────────────────────────────────────────────────────────────────────

REGION="us-east-1"
STACK_NAME="ai-camera-gpu"

# ── Get instance ID from CloudFormation stack ──────────────────────────────
get_instance_id() {
  aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" \
    --output text --region $REGION 2>/dev/null
}

get_backend_url() {
  aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='BackendURL'].OutputValue" \
    --output text --region $REGION 2>/dev/null
}

get_elastic_ip() {
  aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='ElasticIPAddress'].OutputValue" \
    --output text --region $REGION 2>/dev/null
}

case "$1" in

  # ── deploy: First-time setup ──────────────────────────────────────────────
  deploy)
    echo "🚀 Deploying EC2 GPU stack..."
    echo ""
    read -p "Enter your Key Pair name: " KEY_PAIR
    read -p "Enter your IP (from whatismyip.com, format: 1.2.3.4/32): " MY_IP

    aws cloudformation deploy \
      --template-file aws/ec2-gpu.yml \
      --stack-name $STACK_NAME \
      --parameter-overrides \
        KeyPairName="$KEY_PAIR" \
        YourHomeIP="$MY_IP" \
      --capabilities CAPABILITY_NAMED_IAM \
      --region $REGION

    echo ""
    echo "✅ Deployed! Your backend URL:"
    get_backend_url
    ;;

  # ── start: Start the GPU instance ────────────────────────────────────────
  start)
    INSTANCE_ID=$(get_instance_id)
    echo "⚡ Starting GPU instance: $INSTANCE_ID"
    aws ec2 start-instances --instance-ids $INSTANCE_ID --region $REGION > /dev/null

    echo "⏳ Waiting for instance to be running (~30 sec)..."
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

    echo "⏳ Waiting for backend to start (~60 sec)..."
    sleep 60

    URL=$(get_backend_url)
    echo ""
    echo "✅ GPU Backend is LIVE!"
    echo "   URL: $URL"
    echo "   Docs: $URL/docs"
    echo ""
    echo "💡 Update your frontend: VITE_API_URL=$URL"
    ;;

  # ── stop: Stop the GPU instance (saves credits) ──────────────────────────
  stop)
    INSTANCE_ID=$(get_instance_id)
    echo "🛑 Stopping GPU instance: $INSTANCE_ID"
    aws ec2 stop-instances --instance-ids $INSTANCE_ID --region $REGION > /dev/null
    echo "✅ Instance stopped — $0.00/hour while stopped"
    ;;

  # ── status: Check current state ──────────────────────────────────────────
  status)
    INSTANCE_ID=$(get_instance_id)
    STATE=$(aws ec2 describe-instances \
      --instance-ids $INSTANCE_ID \
      --query "Reservations[0].Instances[0].State.Name" \
      --output text --region $REGION 2>/dev/null)
    URL=$(get_backend_url)

    echo "═══════════════════════════════════"
    echo "  AI Camera GPU Backend Status"
    echo "═══════════════════════════════════"
    echo "  Instance: $INSTANCE_ID"
    echo "  State:    $STATE"
    echo "  URL:      $URL"
    echo "═══════════════════════════════════"

    if [ "$STATE" = "running" ]; then
      echo "  Health:   $(curl -s $URL/health | python3 -m json.tool 2>/dev/null || echo 'starting...')"
    fi
    ;;

  # ── ssh: SSH into the instance ────────────────────────────────────────────
  ssh)
    IP=$(get_elastic_ip)
    KEY_FILE="${2:-ai-camera-key.pem}"
    echo "🔌 Connecting to $IP..."
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$IP
    ;;

  # ── logs: Tail backend logs ───────────────────────────────────────────────
  logs)
    IP=$(get_elastic_ip)
    KEY_FILE="${2:-ai-camera-key.pem}"
    echo "📋 Tailing backend logs on $IP..."
    ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no ubuntu@$IP \
      "journalctl -u ai-camera -f"
    ;;

  *)
    echo "Usage: $0 {deploy|start|stop|status|ssh|logs}"
    echo ""
    echo "  deploy  → First-time CloudFormation setup"
    echo "  start   → Start GPU instance (costs \$0.16/hr)"
    echo "  stop    → Stop instance (\$0.00/hr)"
    echo "  status  → Check if running"
    echo "  ssh     → SSH into instance"
    echo "  logs    → Tail FastAPI logs"
    ;;
esac
