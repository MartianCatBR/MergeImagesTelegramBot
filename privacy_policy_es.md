# Política de privacidad — MergeImages

MergeImages procesa archivos y mensajes enviados voluntariamente por los usuarios para realizar las operaciones solicitadas. Las imágenes, PDFs, GIFs, textos OCR y contenidos de códigos QR procesados no se envían automáticamente al administrador.

El servicio puede procesar el ID de Telegram, el nombre público, el idioma, las preferencias, los eventos de uso y los tickets de soporte. Los registros generales no deben almacenar nombres de usuario; la columna heredada puede conservarse por compatibilidad. El nombre de usuario solo se utiliza en el flujo de tickets cuando sea necesario para contactar al usuario.

El administrador puede recibir métricas agregadas, como cantidades de acciones, imágenes generadas, códigos QR, operaciones OCR, conversiones y usuarios activos. Cuando el usuario abre un ticket, el texto, el nombre público, el nombre de usuario y el ID de Telegram pueden enviarse al administrador para investigar y responder. No incluyas contraseñas, tokens ni documentos privados en los tickets.

La búsqueda visual requiere confirmación explícita antes de enviar una imagen a Telegra.ph o Catbox.moe y utilizarla después con Google Lens. Estos servicios tienen sus propias políticas de conservación. Los endpoints del Mini App usan `initData` firmado por Telegram; CORS se restringe mediante `MINIAPP_ALLOWED_ORIGINS`, y CORS no sustituye la autenticación. El diagnóstico está restringido al administrador.

El mensaje de apoyo puede enviarse como máximo una vez después de siete días de uso y, por separado, una vez cuando se alcanza la cuota de créditos. El operador debe definir los plazos de conservación de archivos temporales, base de datos, registros y tickets, y ofrecer eliminación o anonimización. Nunca publiques tokens, claves API, bases de datos de producción ni credenciales.
