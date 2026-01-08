import os
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from dotenv import load_dotenv

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

@app.route('/api/gerar-pdf/<int:id>')
@login_required
def gerar_pdf(id):
    try:
        # Buscar orçamento
        response = supabase.table('lorena-orcamentos').select('*').eq('id', id).eq('usuario_id', session['user_id']).execute()
        
        if not response.data:
            return "Orçamento não encontrado", 404
        
        orcamento = response.data[0]
        dados = json.loads(orcamento['dados_completos'])
        
        # Buscar dados do usuário
        user_response = supabase.table('lorena-usuarios').select('*').eq('id', session['user_id']).execute()
        user = user_response.data[0]
        
        # Criar PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilo personalizado
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        # Título
        elements.append(Paragraph("PROPOSTA DE HONORÁRIOS", title_style))
        elements.append(Paragraph("Perícia Psicológica", subtitle_style))
        elements.append(Spacer(1, 10*mm))
        
        # Informações do profissional
        prof_data = [
            ['PSICÓLOGO(A) PERITO(A)', ''],
            ['Nome:', user['nome_completo']],
            ['CRP:', user['numero_crp'] or 'Não informado'],
            ['Telefone:', user['telefone'] or 'Não informado'],
            ['Email:', user['email']]
        ]
        
        prof_table = Table(prof_data, colWidths=[45*mm, 120*mm])
        prof_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(prof_table)
        elements.append(Spacer(1, 8*mm))
        
        # Informações do cliente
        client_data = [
            ['DADOS DO CLIENTE', ''],
            ['Nome:', orcamento['nome_cliente']],
            ['Telefone:', orcamento.get('telefone_cliente') or 'Não informado'],
            ['Tipo de Serviço:', orcamento['tipo_servico']],
            ['Data:', datetime.fromisoformat(orcamento['created_at'].replace('Z', '+00:00')).strftime('%d/%m/%Y')]
        ]
        
        client_table = Table(client_data, colWidths=[45*mm, 120*mm])
        client_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(client_table)
        elements.append(Spacer(1, 8*mm))
        
        # Detalhamento dos valores
        valores_data = [
            ['DETALHAMENTO DOS HONORÁRIOS', ''],
            ['Valor Base:', f"R$ {orcamento['valor_base']:.2f}"],
            ['Taxa Horária:', f"R$ {orcamento['taxa_horaria']:.2f}"],
            ['Horas de Análise:', f"{orcamento['horas_analise']:.1f}h"],
            ['Custo Horas de Análise:', f"R$ {orcamento['custo_horas_analise']:.2f}"],
        ]
        
        if orcamento['valor_ajustado'] and orcamento['valor_ajustado'] != orcamento['valor_base']:
            valores_data.append(['Valor com Ajustes:', f"R$ {orcamento['valor_ajustado']:.2f}"])
        
        valores_data.append(['', ''])
        valores_data.append(['VALOR TOTAL:', f"R$ {orcamento['valor_total']:.2f}"])
        
        valores_table = Table(valores_data, colWidths=[120*mm, 45*mm])
        valores_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BACKGROUND', (0, 1), (0, -2), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, 1), (0, -2), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e9')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor('#2e7d32')),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('BOX', (0, -1), (-1, -1), 1.5, colors.HexColor('#2e7d32')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(valores_table)
        
        if orcamento.get('observacoes'):
            elements.append(Spacer(1, 8*mm))
            obs_style = ParagraphStyle(
                'Obs',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#666666')
            )
            elements.append(Paragraph(f"<b>Observações:</b><br/>{orcamento['observacoes']}", obs_style))
        
        # Rodapé
        elements.append(Spacer(1, 15*mm))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER
        )
        elements.append(Paragraph(f"Proposta gerada em {datetime.now().strftime('%d/%m/%Y às %H:%M')}", footer_style))
        elements.append(Paragraph(f"Número da proposta: {orcamento['numero']}", footer_style))
        
        # Construir PDF
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"proposta_{orcamento['numero']}.pdf"
        )
    except Exception as e:
        return f"Erro ao gerar PDF: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
