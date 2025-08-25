#!/bin/sh
case "$1" in
  *Username*) echo "x-access-token" ;;
  *Password*) cat /etc/zaas/.github_token ;;
  *) echo "" ;;
esac