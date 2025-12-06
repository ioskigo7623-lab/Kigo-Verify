import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, InputText, Modal
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")
DATA_FILE = "verify_settings.json"

def load_settings():
    if not os.path.exists(DATA_FILE):
        save_settings({
            "verify_code": None,
            "verify_channel": None,
            "apply_channel": None,
            "log_channel": None,
            "member_role": None,
            "unverified_role: None
        })
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

settings = load_settings()

intents = discord.Intents.dafault()
intents.members = True
bot = commands.Bot(command_prefix="?$", intents=intents)

#認証コード入力モーダル
class CodeInputModal(Modal, title="認証コードの入力"):
    code = InputText(label="認証コードを入力してください")
    
    async def callback(self, interaction: discord.Interaction):
        settings = load_settings()
        verify_code = settings["verify_code"]
        
        member_role_id = settings.get("member_role")
        unverified_role_id = settings.get("unverified_role")
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        
        embed = discord.Embed()
        embed.add_field(name="送信した認証コード", value=self.code.value, inline=False)
        
        if self.code.value != verify_code:
            embed.title = "❌認証コードが違います。"
            embed.color = discord.Color.red()
            
            try:
                await interaction.user.send(embed=embed)
            except:
                pass
            
            return await interaction.response.send_message("❌認証コードが違います", ephemeral=True)
            
        embed.title = "✅認証コードで認証を完了しました。"
        embed.color = discord.Color.green()
        
        try:
            await interaction.user.send(embed=embed)
        except:
            pass
        
        try:
            if unverified_role_id:
                unverified_role = guild.get_role(unverified_role_id)
                if unverified_role in member.roles:
                    await member.remove_roles(unverified_role)
                    
            if member_role_id:
                member_role = guild.get_role(member_role_id)
                if member_role not in member.roles:
                    await member.add_roles(member_role)
        except Exception as e:
            print(f"ロール付与エラー: {e}")
            
        return await interaction.response.send_message("✅認証が完了しました。", ephemeral=True)

#認証申請フォーム
class VerifyApplyModal(Modal, title="認証申請フォーム"):
    name = InputText(label="あなたの名前を入力してください")
    inviter = InputText(label="誰から招待されましたか？")
    message = InputText(label="管理者への一言(任意)", required=False)
    
    async def callback(self, interaction: discord.Interaction):
        settings = load_settings()
        apply_channel_id = settings["apply_channel"]
        
        if not apply_channel_id:
            return await interaction.response.send_message("管理側の認証申請設定が完了していません。サーバー管理者に問い合わせてください。", ephemeral=True)
            
        apply_channel = interaction.guild.get_channel(apply_channel_id)
        
        embed = discord.Embed(
            title="🔐 認証申請",
            description=f"ユーザー: {interaction.user.mention}\nID: `{interaction.user.id}`",
            color=discord.Color.yellow()
        )
        embed.add_field(name="名前", value=self.name.value, inline=False)
        embed.add_field(name="招待者", value=self.inviter.value, inline=False)
        embed.add_field(name="一言", value=self.message.value, inline=False)
        
        await apply_channel.send(
            embed=embed,
            view=VerifyApprovalView(
                interaction.user.id,
                self.name.value,
                self.inviter.value,
                self.message.value or "(なし)"
            )
        )
        
        await interaction.response.send_message("📨 認証申請を送信しました。管理者の承認をお待ち下さい。", ephemeral=True)
        
        try:
            dm_embed = discord.Embed(
                title="📬 認証申請が完了しました",
                description="管理者の承認をお待ち下さい。",
                color=discord.Color.blue()
            )
            dm_embed.add_field(name="申請内容", value=None, inline=False)
            dm_embed.add_field(name="あなたの名前を入力してください", value=name, inline=False)
            dm_embed.add_field(name="誰から招待されましたか？", value=inviter, inline=False)
            dm_embed.add_field(name="管理者への一言(任意)", value=message, inline=False)

            await interaction.user.send(embed=dm_embed)
        except:
            pass

class VerifyApprovalView(View):
    def __init__(self, user_id, name, inviter, message):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.name = name
        self.inviter = inviter
        self.message = message
                
    @discord.ui.button(label="✅承認", style=discord.ButtonStyle.green)
        async def approve(self, interaction: discord.Interaction, button: Button):
        settings = load_setting()
        guild = interaction.guild
        user = guild.get_member(self.user_id)
        unverified_role = guild.get_role(settings["unverified_role"])
        member_role = guild.get_role(settings["member_role"])
        log_channel = guild.get_channel(settings["log_channel"])
                
        if unverified_role in user.roles:
            await user.remove_roles(unverified_role)
        if member_role:
            await user.add_roles(member_role)
                
        await interaction.response.edit_message(
            content=f"✅ {user.display_name} を承認しました。"
        )
    try:
        approve_embed = discord.Embed(
            title="✅ 認証申請が承認されました",
            description="メンバーロールが付与されました。",
            color=discord.Color.green()
        )
        await user.send(embed=approve_embed)
    except:
        pass
        
    if log_channel:
        log_embed = discord.Embed(
            title=f"✅ {user.mention} の認証申請が承認されました",
            description=None,
            color=discord.Color.green()
        )
        log_embed.add_field(name="あなたの名前を入力してください", value=name, inline=False)
        log_embed.add_field(name="誰から招待されましたか？", value=inviter, inline=False)
        log_embed.add_field(name="管理者への一言(任意), value=message, inline=False)
        log_embed.set_footer(text=f"担当者: {interaction.user.mention}")
        
        await log_channel.send(embed=log_embed)