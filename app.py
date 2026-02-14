import os
import json
from datetime import datetime
from functools import wraps, partial
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from dotenv import load_dotenv

# Imports do ReportLab para o PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

load_dotenv()

# Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Decorator para rotas protegidas
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'logged_in' not in session or 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ============== ROTAS DE AUTENTICAÇÃO ==============

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        try:
            # Buscar usuário no Supabase
            response = supabase.table('lorena-usuarios').select('*').eq('email', email).eq('ativo', True).execute()
            
            if response.data and len(response.data) > 0:
                user = response.data[0]
                if check_password_hash(user['senha_hash'], senha):
                    session['logged_in'] = True
                    session['user_id'] = user['id']
                    session['user_nome'] = user['nome_completo']
                    return redirect(url_for('dashboard'))
            
            return render_template('login.html', erro='Email ou senha incorretos')
        except Exception as e:
            return render_template('login.html', erro='Erro ao fazer login')
    
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form.get('nome_completo')
        email = request.form.get('email')
        senha = request.form.get('senha')
        numero_crp = request.form.get('numero_crp')
        telefone = request.form.get('telefone')
        
        try:
            # Verificar se email já existe
            existing = supabase.table('lorena-usuarios').select('id').eq('email', email).execute()
            if existing.data and len(existing.data) > 0:
                return render_template('registro.html', erro='Email já cadastrado')
            
            # Criar usuário
            senha_hash = generate_password_hash(senha)
            user_data = {
                'nome_completo': nome,
                'email': email,
                'senha_hash': senha_hash,
                'numero_crp': numero_crp,
                'telefone': telefone
            }
            
            response = supabase.table('lorena-usuarios').insert(user_data).execute()
            
            if response.data:
                user = response.data[0]
                # Criar custos fixos padrão
                custos_default = {
                    'usuario_id': user['id'],
                    'aluguel_consultorio': 1000.00,
                    'internet_telefonia': 200.00,
                    'ferramentas_software': 150.00,
                    'anuidade_crp': 100.00,
                    'funcionarios_salarios': 0.00,
                    'outros_custos': 0.00,
                    'horas_trabalhadas_mes': 160
                }
                supabase.table('lorena-custos_fixos').insert(custos_default).execute()
                
                return redirect(url_for('login'))
        except Exception as e:
            return render_template('registro.html', erro=f'Erro ao criar conta: {str(e)}')
    
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============== ROTAS PRINCIPAIS ==============

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', user_nome=session.get('user_nome'))

@app.route('/novo-calculo')
@login_required
def novo_calculo():
    # Buscar custos fixos do usuário
    try:
        response = supabase.table('lorena-custos_fixos').select('*').eq('usuario_id', session['user_id']).execute()
        custos_fixos = response.data[0] if response.data else None
    except:
        custos_fixos = None
    
    return render_template('novo_calculo.html', custos_fixos=custos_fixos)

@app.route('/historico')
@login_required
def historico():
    try:
        response = supabase.table('lorena-orcamentos').select('*').eq('usuario_id', session['user_id']).order('created_at', desc=True).execute()
        orcamentos = response.data
    except:
        orcamentos = []
    
    return render_template('historico.html', orcamentos=orcamentos)

@app.route('/custos-fixos', methods=['GET', 'POST'])
@login_required
def custos_fixos():
    if request.method == 'POST':
        try:
            custos_data = {
                'usuario_id': session['user_id'],
                'aluguel_consultorio': float(request.form.get('aluguel_consultorio', 0)),
                'internet_telefonia': float(request.form.get('internet_telefonia', 0)),
                'ferramentas_software': float(request.form.get('ferramentas_software', 0)),
                'anuidade_crp': float(request.form.get('anuidade_crp', 0)),
                'funcionarios_salarios': float(request.form.get('funcionarios_salarios', 0)),
                'outros_custos': float(request.form.get('outros_custos', 0)),
                'horas_trabalhadas_mes': int(request.form.get('horas_trabalhadas_mes', 160))
            }
            
            # Verificar se já existe
            existing = supabase.table('lorena-custos_fixos').select('id').eq('usuario_id', session['user_id']).execute()
            
            if existing.data and len(existing.data) > 0:
                # Update
                supabase.table('lorena-custos_fixos').update(custos_data).eq('usuario_id', session['user_id']).execute()
            else:
                # Insert
                supabase.table('lorena-custos_fixos').insert(custos_data).execute()
            
            return redirect(url_for('custos_fixos'))
        except Exception as e:
            return render_template('custos_fixos.html', erro=f'Erro ao salvar: {str(e)}')
    
    # GET
    try:
        response = supabase.table('lorena-custos_fixos').select('*').eq('usuario_id', session['user_id']).execute()
        custos = response.data[0] if response.data else None
    except:
        custos = None
    
    return render_template('custos_fixos.html', custos=custos)

@app.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    if request.method == 'POST':
        try:
            update_data = {
                'nome_completo': request.form.get('nome_completo'),
                'numero_crp': request.form.get('numero_crp'),
                'telefone': request.form.get('telefone')
            }
            
            # Atualizar senha se fornecida
            nova_senha = request.form.get('nova_senha')
            if nova_senha:
                update_data['senha_hash'] = generate_password_hash(nova_senha)
            
            supabase.table('lorena-usuarios').update(update_data).eq('id', session['user_id']).execute()
            session['user_nome'] = update_data['nome_completo']
            
            return redirect(url_for('configuracoes'))
        except Exception as e:
            return render_template('configuracoes.html', erro=f'Erro ao atualizar: {str(e)}')
    
    # GET
    try:
        response = supabase.table('lorena-usuarios').select('*').eq('id', session['user_id']).execute()
        user = response.data[0] if response.data else None
    except:
        user = None
    
    return render_template('configuracoes.html', user=user)

# ============== API ENDPOINTS ==============

@app.route('/api/salvar-orcamento', methods=['POST'])
@login_required
def salvar_orcamento():
    try:
        data = request.json
        
        # Gerar número único
        numero = f"PER-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        orcamento_data = {
            'usuario_id': session['user_id'],
            'numero': numero,
            'nome_cliente': data.get('nome_cliente'),
            'telefone_cliente': data.get('telefone_cliente'),
            'tipo_servico': data.get('tipo_servico'),
            'valor_base': float(data.get('valor_base', 0)),
            'horas_analise': float(data.get('horas_analise', 0)),
            'grau_urgencia': int(data.get('grau_urgencia', 0)),
            'grau_especificidade': int(data.get('grau_especificidade', 0)),
            'grau_complexidade': int(data.get('grau_complexidade', 0)),
            'ajustes': json.dumps(data.get('ajustes', [])),
            'valor_ajustado': float(data.get('valor_ajustado', 0)),
            'taxa_horaria': float(data.get('taxa_horaria', 0)),
            'custo_horas_analise': float(data.get('custo_horas_analise', 0)),
            'subtotal_fixo': float(data.get('subtotal_fixo', 0)),
            'valor_total': float(data.get('valor_total', 0)),
            'opcoes_pagamento': json.dumps(data.get('opcoes_pagamento', [])),
            'observacoes': data.get('observacoes'),
            'dados_completos': json.dumps(data)
        }
        
        response = supabase.table('lorena-orcamentos').insert(orcamento_data).execute()
        
        if response.data:
            return jsonify({'success': True, 'id': response.data[0]['id'], 'numero': numero})
        else:
            return jsonify({'success': False, 'error': 'Erro ao salvar orçamento'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orcamento/<int:id>')
@login_required
def get_orcamento(id):
    try:
        response = supabase.table('lorena-orcamentos').select('*').eq('id', id).eq('usuario_id', session['user_id']).execute()
        
        if response.data and len(response.data) > 0:
            return jsonify(response.data[0])
        else:
            return jsonify({'error': 'Orçamento não encontrado'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/deletar-orcamento/<int:id>', methods=['DELETE'])
@login_required
def deletar_orcamento(id):
    try:
        supabase.table('lorena-orcamentos').delete().eq('id', id).eq('usuario_id', session['user_id']).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# =======================================================
# NOVA ROTA DE GERAÇÃO DE PDF (CLEAN & ALTO PADRÃO)
# =======================================================

@app.route('/api/gerar-pdf/<int:id>')
@login_required
def gerar_pdf(id):
    try:
        # 1. Buscar dados do Orçamento
        response = supabase.table('lorena-orcamentos').select('*').eq('id', id).eq('usuario_id', session['user_id']).execute()
        
        if not response.data:
            return "Orçamento não encontrado", 404
        
        orcamento = response.data[0]
        
        # CORREÇÃO DO ERRO: Se o supabase retornou uma string JSON, converte para dict
        if isinstance(orcamento, str):
            orcamento = json.loads(orcamento)

        # 2. Buscar dados do Usuário
        user_response = supabase.table('lorena-usuarios').select('*').eq('id', session['user_id']).execute()
        
        if not user_response.data:
            return "Usuário não encontrado", 404
            
        user = user_response.data[0]
        
        # CORREÇÃO DO ERRO: Mesma segurança para o usuário
        if isinstance(user, str):
            user = json.loads(user)
        
        # 3. Configuração do PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            topMargin=25*mm,
            bottomMargin=20*mm, 
            leftMargin=20*mm, 
            rightMargin=20*mm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Cores e Estilos
        COLOR_PRIMARY = colors.HexColor('#059669')
        COLOR_DARK = colors.HexColor('#111827')
        COLOR_GRAY = colors.HexColor('#6b7280')
        
        # Estilos Personalizados
        style_title = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, textColor=COLOR_DARK, alignment=TA_RIGHT, spaceAfter=2)
        style_subtitle = ParagraphStyle('DocSub', parent=styles['Normal'], fontSize=10, textColor=COLOR_PRIMARY, alignment=TA_RIGHT)
        style_section = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=12, textColor=COLOR_PRIMARY, spaceBefore=15, spaceAfter=8, textTransform='uppercase')
        style_label = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, textColor=COLOR_GRAY, leading=11)
        style_value = ParagraphStyle('Value', parent=styles['Normal'], fontSize=10, textColor=COLOR_DARK, leading=12, fontName='Helvetica-Bold')
        style_normal = ParagraphStyle('NormalText', parent=styles['Normal'], fontSize=10, textColor=COLOR_DARK, leading=14, alignment=TA_JUSTIFY)
        
        # --- CABEÇALHO ---
        logo_path = os.path.join(app.static_folder, 'logo.png')
        header_content = []
        
        if os.path.exists(logo_path):
            img = Image(logo_path, width=45*mm, height=45*mm, kind='proportional')
            img.hAlign = 'LEFT'
            header_content.append(img)
        else:
            header_content.append(Paragraph("<b>VALORA</b>", style_section))

        # Tratamento de datas
        try:
            data_criacao = orcamento.get('created_at', datetime.now().isoformat())
            data_fmt = datetime.fromisoformat(data_criacao.replace('Z', '+00:00')).strftime('%d/%m/%Y')
        except:
            data_fmt = datetime.now().strftime('%d/%m/%Y')

        info_doc = [
            Paragraph("PROPOSTA DE HONORÁRIOS", style_title),
            Paragraph(f"Ref: {orcamento.get('numero', '---')}", style_subtitle),
            Spacer(1, 5),
            Paragraph(f"Emitido em: {data_fmt}", ParagraphStyle('Date', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=9, textColor=COLOR_GRAY))
        ]
        
        header_table = Table([[header_content[0] if header_content else "", info_doc]], colWidths=[85*mm, 85*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(header_table)
        
        elements.append(Spacer(1, 5*mm))
        elements.append(Table([['']], colWidths=[170*mm], style=TableStyle([('LINEBELOW', (0,0), (-1,-1), 1, COLOR_PRIMARY)])))
        elements.append(Spacer(1, 10*mm))

        # --- DADOS DAS PARTES ---
        prof_text = [
            [Paragraph("PROFISSIONAL", style_section)],
            [Paragraph("Nome Completo:", style_label)],
            [Paragraph(user.get('nome_completo', ''), style_value)],
            [Spacer(1, 3)],
            [Paragraph("Registro (CRP):", style_label)],
            [Paragraph(user.get('numero_crp') or 'Não informado', style_value)],
            [Spacer(1, 3)],
            [Paragraph("Contato:", style_label)],
            [Paragraph(user.get('email', ''), style_value)],
            [Paragraph(user.get('telefone') or '', style_value)]
        ]

        client_text = [
            [Paragraph("CLIENTE", style_section)],
            [Paragraph("Nome / Responsável:", style_label)],
            [Paragraph(orcamento.get('nome_cliente', ''), style_value)],
            [Spacer(1, 3)],
            [Paragraph("Telefone:", style_label)],
            [Paragraph(orcamento.get('telefone_cliente') or 'Não informado', style_value)],
            [Spacer(1, 3)],
            [Paragraph("Serviço:", style_label)],
            [Paragraph(orcamento.get('tipo_servico', ''), style_value)]
        ]

        partes_table = Table([[Table(prof_text, colWidths=[80*mm]), Table(client_text, colWidths=[80*mm])]], colWidths=[85*mm, 85*mm])
        partes_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(partes_table)
        elements.append(Spacer(1, 15*mm))

        # --- TABELA FINANCEIRA ---
        elements.append(Paragraph("DETALHAMENTO DO INVESTIMENTO", style_section))
        elements.append(Spacer(1, 3*mm))

        # Valores seguros (float)
        try:
            val_base = float(orcamento.get('valor_base', 0))
            val_ajustado = float(orcamento.get('valor_ajustado', 0))
            val_total = float(orcamento.get('valor_total', 0))
            custo_hora = float(orcamento.get('custo_horas_analise', 0))
        except ValueError:
            val_base = val_ajustado = val_total = custo_hora = 0.0

        f_data = [['Descrição do Serviço', 'Valor']]
        f_data.append(['Valor Base Estimado', f"R$ {val_base:.2f}"])
        f_data.append(['Custo Hora Técnica', f"R$ {custo_hora:.2f}"])
        
        if val_ajustado and val_ajustado != val_base:
             diferenca = val_ajustado - val_base
             f_data.append(['Ajustes e Especificidades', f"R$ {diferenca:.2f}"])

        t = Table(f_data, colWidths=[130*mm, 40*mm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,0), (-1,0), COLOR_PRIMARY),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('LINEBELOW', (0,0), (-1,0), 1, COLOR_PRIMARY),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('TEXTCOLOR', (0,1), (-1,-1), COLOR_DARK),
            ('FONTSIZE', (0,1), (-1,-1), 10),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,1), (-1,-1), 8),
            ('BOTTOMPADDING', (0,1), (-1,-1), 8),
            ('LINEBELOW', (0,1), (-1,-2), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(t)

        # Total
        elements.append(Spacer(1, 2*mm))
        total_row = ['TOTAL DO INVESTIMENTO', f"R$ {val_total:.2f}"]
        total_table = Table([total_row], colWidths=[130*mm, 40*mm])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ecfdf5')),
            ('TEXTCOLOR', (0,0), (-1,-1), COLOR_PRIMARY),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 12),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('TOPPADDING', (0,0), (-1,-1), 12),
            ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ]))
        elements.append(total_table)

        # --- OBSERVAÇÕES ---
        obs = orcamento.get('observacoes')
        if obs:
            elements.append(Spacer(1, 15*mm))
            elements.append(Paragraph("OBSERVAÇÕES", style_section))
            elements.append(Paragraph(obs.replace('\n', '<br/>'), style_normal))

        # --- RODAPÉ ---
        def footer_bg(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor('#e5e7eb'))
            canvas.setLineWidth(0.5)
            canvas.line(20*mm, 15*mm, 190*mm, 15*mm)
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor('#9ca3af'))
            canvas.drawString(20*mm, 10*mm, "VALORA - Soluções em Psicologia e Perícia")
            canvas.drawRightString(190*mm, 10*mm, f"Página {canvas.getPageNumber()}")
            canvas.restoreState()

        doc.build(elements, onFirstPage=footer_bg, onLaterPages=footer_bg)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"Proposta_Valora_{orcamento.get('numero', 'doc')}.pdf"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Erro ao gerar PDF: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)