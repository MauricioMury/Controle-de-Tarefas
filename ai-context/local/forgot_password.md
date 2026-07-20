# Como funciona o endpoint **Forgot Password**

## Visão geral
O endpoint `POST /api/v1/auth/forgot-password` gera um token de redefinição de senha de curta duração (15 min) para o usuário indicado por e‑mail.  
Ele é usado na fase **4 – Recuperação & Reset de Senha**.

## Fluxo passo a passo
1. **Requisição**  
   ```json
   {
     "email": "usuario@exemplo.com"
   }

2. **Validação**
Busca o usuário pelo e‑mail.
Se não existir → 404 User not found.

3. **Geração do token**
PasswordResetToken.generate(user_id, ttl_minutes=15) cria um UUID e define expires_at.
O token é salvo na tabela password_reset_tokens.

4.  **Resposta**

{
  "reset_token": "<uuid‑hex>",
  "expires_in": 900   // segundos (15 min)
}

5. **Modelo de Dados**

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: int
    user_id: int  # FK → users.id
    token: str    # UUID (hex), único
    expires_at: datetime

6. **Segurança**
Token é único e expira rapidamente.
Não contém informações sensíveis; apenas um UUID.
O endpoint não revela se o e‑mail existe (poderia ser ajustado para resposta genérica).    
