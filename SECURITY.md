# Segurança

## Escopo

Relatos de segurança são relevantes quando envolvem, por exemplo:

- workflows e cadeia de suprimentos;
- exposição de segredos, tokens ou credenciais;
- execução indevida de código;
- injeção em consultas, scripts ou artefatos gerados;
- comprometimento de dependências ou do ambiente de publicação.

Erros estatísticos, divergências de fonte e problemas de qualidade de dados devem ser tratados como issues de dados, não como vulnerabilidades.

## Como relatar

Não abra uma issue pública para uma vulnerabilidade ainda não corrigida.

Prefira o mecanismo privado de reporte de vulnerabilidade do GitHub quando ele estiver disponível. Caso não esteja, entre em contato de forma privada com o mantenedor pelo perfil do GitHub.

Inclua, quando possível:

- descrição objetiva do problema;
- componente afetado;
- passos mínimos para reprodução;
- impacto observado ou plausível;
- evidências sem dados pessoais ou segredos;
- sugestão de mitigação, se houver.

## Dados e segredos

Nunca envie ao repositório:

- credenciais;
- arquivos `.env`;
- tokens de API;
- chaves privadas;
- cookies ou sessões autenticadas;
- dumps privados;
- dados pessoais que não possam ser redistribuídos.

O projeto trabalha com dados públicos da ANP e não exige o versionamento de dados brutos ou processados para reproduzir o código.
