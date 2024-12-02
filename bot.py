import discord
from discord.ext import commands
from datetime import datetime, timedelta, time
import asyncio
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configurações do bot
intents = discord.Intents.default()
intents.message_content = True  # Permite que o bot leia o conteúdo das mensagens
intents.messages = True         # Necessário para gerenciar mensagens

bot = commands.Bot(command_prefix='!', intents=intents)

# IDs dos canais
CANAL_FREQUENCIA_ID = 1228673076888080414  # Canal onde os usuários enviam comandos
CANAL_REGISTROS_ID = 1313234259959480470   # Canal onde os registros serão enviados

# Variáveis globais
tolerancia_inicio = timedelta(minutes=10)
tolerancia_fim = timedelta(minutes=10)
hora_inicio_manha = time(8, 0, 0)
hora_fim_manha = time(12, 0, 0)
hora_inicio_tarde = time(13, 0, 0)
hora_fim_tarde = time(17, 0, 0)
hora_daily = time(17, 30, 0)
ultima_data_registro = None  # Armazena a última data registrada

# Função para enviar registro ao canal de registros
async def enviar_registro(user_name, acao, timestamp, passou_tolerancia, passou_horario):
    global ultima_data_registro
    canal_registros = bot.get_channel(CANAL_REGISTROS_ID)
    if canal_registros is not None:
        data_atual = timestamp.strftime('%d/%m/%Y')
        
        # Se a data mudou, enviar um separador ou cabeçalho
        if ultima_data_registro != data_atual:
            ultima_data_registro = data_atual
            # Enviar uma mensagem de cabeçalho para a nova data
            await canal_registros.send(f"\n📅 **Registros do dia {data_atual}** 📅\n{'='*40}")

        # Emojis
        emoji_usuario = '👤'
        emoji_acao = '✅'
        emoji_hora = '⏰'
        emoji_tolerancia = '⏳'
        emoji_horario = '🕒'
        
        # Formatação da mensagem
        mensagem = (
            f"{emoji_usuario} **Usuário:** {user_name}\n"
            f"{emoji_acao} **Ação:** {acao}\n"
            f"{emoji_hora} **Hora:** {timestamp.strftime('%H:%M:%S')}\n"
            f"{emoji_tolerancia} **Passou da tolerância:** {'Sim' if passou_tolerancia else 'Não'}\n"
            f"{emoji_horario} **Passou do horário:** {'Sim' if passou_horario else 'Não'}"
        )
        await canal_registros.send(mensagem)
    else:
        print(f"Não foi possível encontrar o canal com ID {CANAL_REGISTROS_ID}")

# Comando !iniciar
@bot.command()
async def iniciar(ctx):
    if ctx.channel.id != CANAL_FREQUENCIA_ID:
        return

    agora = datetime.now()
    horario_previsto = datetime.combine(agora.date(), hora_inicio_manha)
    diferenca = agora - horario_previsto

    passou_tolerancia = diferenca > tolerancia_inicio
    passou_horario = agora.time() > hora_inicio_manha

    if passou_tolerancia:
        atraso = diferenca - tolerancia_inicio
        await ctx.send(f"Você está atrasado em {int(atraso.total_seconds()//60)} minutos.")
    else:
        await ctx.send("Bom dia! Registro de início realizado com sucesso.")

    # Enviar registro ao canal de registros
    await enviar_registro(
        ctx.author.name, 
        'iniciar', 
        agora, 
        passou_tolerancia, 
        passou_horario
    )

# Comando !pausa
@bot.command()
async def pausa(ctx):
    if ctx.channel.id != CANAL_FREQUENCIA_ID:
        return

    agora = datetime.now()
    await ctx.send("Pausa para almoço registrada. Bom almoço!")

    # Não há tolerância para o início da pausa, mas podemos registrar o horário
    await enviar_registro(
        ctx.author.name,
        'pausa',
        agora,
        False,   # Passou tolerância não se aplica
        False    # Passou horário não se aplica
    )

# Comando !volta
@bot.command()
async def volta(ctx):
    if ctx.channel.id != CANAL_FREQUENCIA_ID:
        return

    agora = datetime.now()
    horario_previsto = datetime.combine(agora.date(), hora_inicio_tarde)
    diferenca = agora - horario_previsto

    passou_tolerancia = diferenca > tolerancia_inicio
    passou_horario = agora.time() > hora_inicio_tarde

    if passou_tolerancia:
        atraso = diferenca - tolerancia_inicio
        await ctx.send(f"Você está atrasado em {int(atraso.total_seconds()//60)} minutos após o almoço.")
    else:
        await ctx.send("Bem-vindo de volta! Registro realizado com sucesso.")

    # Enviar registro ao canal de registros
    await enviar_registro(
        ctx.author.name,
        'volta',
        agora,
        passou_tolerancia,
        passou_horario
    )

# Comando !finalizar
@bot.command()
async def finalizar(ctx):
    if ctx.channel.id != CANAL_FREQUENCIA_ID:
        return

    agora = datetime.now()
    horario_previsto = datetime.combine(agora.date(), hora_fim_tarde)
    diferenca = horario_previsto - agora

    passou_tolerancia = diferenca < -tolerancia_fim
    passou_horario = agora.time() > hora_fim_tarde

    if passou_tolerancia:
        extra = abs(diferenca + tolerancia_fim)
        await ctx.send(f"Você está saindo {int(extra.total_seconds()//60)} minutos após o horário.")
    else:
        await ctx.send("Até logo! Registro de saída realizado com sucesso.")

    # Enviar registro ao canal de registros
    await enviar_registro(
        ctx.author.name,
        'finalizar',
        agora,
        passou_tolerancia,
        passou_horario
    )

    # Calcular tempo para o daily
    tempo_para_daily = datetime.combine(agora.date(), hora_daily) - agora
    # Chamar a função de limpeza e passar o tempo para o daily
    await limpar_canal_frequencia(tempo_para_daily)

# Função para limpar o canal de frequência
async def limpar_canal_frequencia(tempo_para_daily):
    canal = bot.get_channel(CANAL_FREQUENCIA_ID)
    if canal is not None:
        # Deletar mensagens antigas
        await canal.purge()

        # Mensagem sobre o daily
        if tempo_para_daily.total_seconds() > 0:
            minutos_para_daily = int(tempo_para_daily.total_seconds() // 60)
            mensagem_daily = f"🕒 **Daily em {minutos_para_daily} minutos.**"
        else:
            mensagem_daily = "🕒 **O daily já começou ou já passou.**"

        # Enviar mensagem de limpeza e daily juntos
        mensagem_combinada = await canal.send(
            f"{mensagem_daily}\n🧹 **O canal foi limpo para o próximo dia. Bom trabalho a todos!**"
        )
        # Excluir a mensagem após 5 minutos
        await mensagem_combinada.delete(delay=300)
    else:
        print(f"Não foi possível encontrar o canal com ID {CANAL_FREQUENCIA_ID}")

# Evento de inicialização do bot
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    canal = bot.get_channel(CANAL_FREQUENCIA_ID)
    if canal is not None:
        await canal.send("O bot está online e pronto para uso!")
    else:
        print(f"Não foi possível encontrar o canal com ID {CANAL_FREQUENCIA_ID}")

# Handler para comandos não encontrados
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        comandos_disponiveis = ['!iniciar', '!pausa', '!volta', '!finalizar']
        mensagem = "Comando não reconhecido. Aqui estão os comandos disponíveis:\n"
        for cmd in comandos_disponiveis:
            mensagem += f"- {cmd}\n"
        await ctx.send(mensagem)
    else:
        # Se o erro não for CommandNotFound, podemos imprimir no console ou tratar de outra forma
        print(f"Ocorreu um erro: {error}")

bot.run(TOKEN)
