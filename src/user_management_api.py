"""
用户管理 API 接口
遵循项目 API 设计规范
"""
from flask import Flask, request, jsonify
from functools import wraps
from datetime import datetime
from typing import Optional, Dict, Any, List

app = Flask(__name__)

# 内存数据库模拟
users_db: Dict[str, Dict[str, Any]] = {}
user_id_counter = 1


# ==================== 响应格式工具函数 ====================

def success_response(data: Any, meta: Optional[Dict] = None, status_code: int = 200):
    """构建成功响应"""
    response = {
        "data": data,
        "error": None
    }
    if meta:
        response["meta"] = meta
    return jsonify(response), status_code


def error_response(code: str, message: str, details: Optional[str] = None, status_code: int = 400):
    """构建错误响应"""
    error_obj = {
        "code": code,
        "message": message
    }
    if details:
        error_obj["details"] = details
    return jsonify({
        "data": None,
        "error": error_obj
    }), status_code


# ==================== 身份验证中间件 ====================

def require_auth(f):
    """Bearer 令牌验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return error_response("AUTH_MISSING", "未提供认证令牌", status_code=401)
        if not auth_header.startswith('Bearer '):
            return error_response("AUTH_INVALID", "无效的认证令牌格式", status_code=401)
        # TODO: 实际项目中应验证 JWT 令牌
        return f(*args, **kwargs)
    return decorated_function


# ==================== 数据验证 ====================

def validate_user_data(data: Dict) -> Optional[str]:
    """验证用户数据"""
    required_fields = ['name', 'email']
    for field in required_fields:
        if field not in data:
            return f"缺少必填字段: {field}"
    if '@' not in data['email']:
        return "邮箱格式无效"
    return None


# ==================== 路由定义 ====================

@app.route('/api/v1/users', methods=['GET'])
@require_auth
def get_users():
    """获取用户列表 (支持分页和过滤)"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    status = request.args.get('status')

    users_list = list(users_db.values())

    # 状态过滤
    if status:
        users_list = [u for u in users_list if u.get('status') == status]

    # 分页
    total = len(users_list)
    start = (page - 1) * limit
    end = start + limit
    paginated_users = users_list[start:end]

    return success_response(
        data=paginated_users,
        meta={
            "page": page,
            "limit": limit,
            "total": total
        }
    )


@app.route('/api/v1/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id: int):
    """获取单个用户详情"""
    user = users_db.get(str(user_id))
    if not user:
        return error_response("USER_NOT_FOUND", "用户不存在", status_code=404)
    return success_response(data=user)


@app.route('/api/v1/users', methods=['POST'])
@require_auth
def create_user():
    """创建新用户"""
    data = request.get_json()
    if not data:
        return error_response("INVALID_JSON", "请求体必须为 JSON 格式")

    # 数据验证
    validation_error = validate_user_data(data)
    if validation_error:
        return error_response("VALIDATION_ERROR", validation_error, status_code=400)

    global user_id_counter
    user_id = str(user_id_counter)
    user_id_counter += 1

    new_user = {
        "id": user_id,
        "name": data['name'],
        "email": data['email'],
        "status": data.get('status', 'active'),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }

    users_db[user_id] = new_user
    return success_response(data=new_user, status_code=201)


@app.route('/api/v1/users/<int:user_id>', methods=['PUT'])
@require_auth
def update_user(user_id: int):
    """更新用户"""
    user = users_db.get(str(user_id))
    if not user:
        return error_response("USER_NOT_FOUND", "用户不存在", status_code=404)

    data = request.get_json()
    if not data:
        return error_response("INVALID_JSON", "请求体必须为 JSON 格式")

    # 更新字段
    if 'name' in data:
        user['name'] = data['name']
    if 'email' in data:
        if '@' not in data['email']:
            return error_response("VALIDATION_ERROR", "邮箱格式无效", status_code=400)
        user['email'] = data['email']
    if 'status' in data:
        user['status'] = data['status']

    user['updated_at'] = datetime.utcnow().isoformat()
    return success_response(data=user)


@app.route('/api/v1/users/<int:user_id>', methods=['DELETE'])
@require_auth
def delete_user(user_id: int):
    """删除用户"""
    user = users_db.get(str(user_id))
    if not user:
        return error_response("USER_NOT_FOUND", "用户不存在", status_code=404)

    del users_db[str(user_id)]
    return success_response(data=None, status_code=200)


# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return error_response("NOT_FOUND", "请求的资源不存在", status_code=404)


@app.errorhandler(405)
def method_not_allowed(error):
    return error_response("METHOD_NOT_ALLOWED", "不支持的 HTTP 方法", status_code=405)


@app.errorhandler(500)
def internal_error(error):
    return error_response("INTERNAL_ERROR", "服务器内部错误", status_code=500)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
