# Fase 5 — Cloud Computing (AWS) e Segurança (ISO 27001/27002)

**Grupo 1TIAO — FarmTech Solutions**

Este documento descreve a infraestrutura em nuvem que sustenta o sistema da
fazenda e as práticas de segurança da informação adotadas, alinhadas às normas
**ISO/IEC 27001** (sistema de gestão de segurança da informação) e **ISO/IEC
27002** (controles de segurança).

> As capturas de tela da configuração real ficam em `docs/prints_aws/` e são
> referenciadas no README principal do projeto.

---

## 1. Visão geral da arquitetura em nuvem

```
   [ESP32 / Sensores]                 [Imagens da lavoura]
          |  (Fase 3)                        |  (Fase 6)
          v                                  v
   +-------------------------------------------------+
   |   Aplicação FarmTech (EC2 ou execução local)     |
   |   - Dashboard Streamlit (app.py)                 |
   |   - Banco de dados (SQLite local / RDS opcional) |
   |   - Modelos de ML (Fase 4)                       |
   +-------------------------------------------------+
          |  publica eventos / limiares
          v
   +-------------------------------------------------+
   |   Amazon SNS  (Tópico: alertas-fazenda)          |
   |   - Assinatura por e-mail (funcionários)         |
   |   - Envio de SMS direto                          |
   +-------------------------------------------------+
          |                         |
          v                         v
     [E-mail]                    [SMS]
```

Componentes AWS utilizados (mínimo viável da Fase 7):

| Serviço        | Uso no projeto                                             |
|----------------|------------------------------------------------------------|
| **Amazon SNS** | Tópico de alertas; entrega de e-mail e SMS aos funcionários |
| **IAM**        | Usuário/*role* com permissão mínima (`sns:Publish`)         |
| **CloudWatch** | Logs e métricas dos disparos (monitoramento)                |
| **EC2** (opc.) | Hospedar o dashboard 24/7 (t3.micro)                        |
| **RDS** (opc.) | Banco gerenciado (PostgreSQL) caso saia do SQLite           |

---

## 2. Provisionamento do Amazon SNS (passo a passo)

1. **Criar o tópico**: SNS → *Topics* → *Create topic* → tipo *Standard* →
   nome `alertas-fazenda`. Copie o **ARN** gerado.
2. **Assinar e-mail**: no tópico → *Create subscription* → *Protocol: Email* →
   informe o e-mail do funcionário → confirme o link recebido na caixa de entrada.
3. **SMS**: habilite *Text messaging (SMS)* na conta e, se necessário, saia do
   *sandbox* para enviar a números não verificados.
4. **Credenciais**: crie um usuário IAM com a política mínima abaixo e gere
   *Access Key*/*Secret Key*. Coloque-as no `.env` do projeto.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["sns:Publish"],
      "Resource": "arn:aws:sns:us-east-1:<conta>:alertas-fazenda"
    }
  ]
}
```

5. **`.env`** (ver `.env.example`):

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:<conta>:alertas-fazenda
EMAIL_DEST=funcionario@fazenda.com.br
PHONE_DEST=+5511999999999
```

> Sem credenciais válidas, o serviço (`fase7_alertas/alerta_aws.py`) entra
> automaticamente em **MODO SIMULADO** e imprime o que seria enviado.

---

## 3. Segurança da informação (ISO 27001 / 27002)

A ISO 27001 define o **SGSI** (processo de gestão de risco); a ISO 27002 traz
o **catálogo de controles**. Mapeamento prático no projeto:

| Controle (ISO 27002)                       | Como aplicamos                                                                 |
|--------------------------------------------|-------------------------------------------------------------------------------|
| **A.5 Políticas de segurança**             | Documentação clara de acesso e uso (este arquivo + README).                   |
| **A.8 Gestão de ativos**                   | Inventário de dados (sensores, imagens) e do banco; dados versionados.        |
| **A.9 Controle de acesso**                 | Usuário IAM com **privilégio mínimo** (`sns:Publish`), sem uso de root.       |
| **A.10 Criptografia**                      | Segredos fora do código (`.env`), HTTPS nas chamadas, SNS sob TLS.            |
| **A.12 Segurança operacional**             | **Logs** de alertas (`ALERTAS_LOG` + CloudWatch); tratamento de exceções.     |
| **A.12.3 Cópias de segurança**             | Banco SQLite versionável / RDS com *snapshots* automáticos (opcional).        |
| **A.16 Gestão de incidentes**             | Alertas automáticos (Fase 7) sinalizam anomalias em tempo hábil.              |
| **A.5.30 / Continuidade**                  | Modo simulado garante operação degradada se a nuvem estiver indisponível.     |

Princípios reforçados:

- **Princípio do menor privilégio**: a chave usada só pode publicar no tópico.
- **Segregação de segredos**: nada de credencial *hardcoded* — tudo em `.env`
  (que fica no `.gitignore`).
- **Defesa em profundidade**: validação de limiares na borda (ESP32), na
  aplicação (Python) e auditoria no banco/CloudWatch.
- **Confidencialidade, Integridade e Disponibilidade (CIA)** como guia das
  decisões de arquitetura.

---

## 4. Custos e boas práticas

- SNS cobra por mensagem (e-mail é gratuito até cota alta; SMS tem custo por
  destino/país). Para a demo, o **modo simulado** evita qualquer custo.
- Use *budgets/alarms* no CloudWatch para evitar surpresas.
- Em produção, prefira **roles** (instância EC2 com *instance profile*) a
  *access keys* estáticas.

---

## 5. Prints da solução (anexar em `docs/prints_aws/`)

Sugestão de capturas para o README/vídeo:

1. Tópico SNS criado (com ARN).
2. Assinatura de e-mail **confirmada**.
3. Política IAM de privilégio mínimo.
4. E-mail/SMS recebido com a ação corretiva.
5. (Opcional) Logs no CloudWatch.
