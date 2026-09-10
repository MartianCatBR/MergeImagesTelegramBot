# Política de Privacidade — MergeImages

O MergeImages processa arquivos e mensagens enviados voluntariamente pelos usuários para executar as operações solicitadas. Imagens, PDFs, GIFs, textos de OCR e conteúdos de QR Code processados não são enviados automaticamente ao administrador.

O serviço pode processar Telegram ID, nome público, idioma, preferências, eventos de uso e tickets de suporte. Os logs gerais não devem armazenar usernames; a coluna legada pode permanecer por compatibilidade. Usernames são usados apenas no fluxo de tickets quando necessário para contactar o usuário.

Métricas agregadas podem ser compartilhadas com o administrador, incluindo quantidades de ações, imagens geradas, QR Codes, operações OCR, conversões e usuários ativos. Quando o usuário abre um ticket, o texto, nome público, username e Telegram ID podem ser enviados ao administrador para investigar e responder. Não inclua senhas, tokens ou documentos privados em tickets.

A busca visual exige confirmação explícita antes de enviar uma imagem ao Telegra.ph ou Catbox.moe e depois usá-la no Google Lens. Esses serviços têm suas próprias políticas de retenção. Os endpoints do Mini App usam `initData` assinado pelo Telegram; o CORS é restringido por `MINIAPP_ALLOWED_ORIGINS`, e CORS não substitui autenticação. O diagnóstico é exclusivo do administrador.

A mensagem de apoio pode ser enviada no máximo uma vez após sete dias de uso e, separadamente, uma vez quando a cota de créditos for atingida. O operador deve definir prazos de retenção para arquivos temporários, banco, logs e tickets, além de oferecer exclusão ou anonimização. Nunca publique tokens, chaves de API, bancos de produção ou credenciais.
