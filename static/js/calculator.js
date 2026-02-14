// Dados da calculadora
const calculatorData = {
    step: 1,
    taxaHoraria: window.TAXA_HORARIA || 37.50,
    nomeCliente: '',
    telefoneCliente: '',
    tipoServico: 'Avaliação Psicológica',
    valorHoraCobrado: 100,
    horasAnalise: 10,
    grauUrgencia: 0,
    grauEspecificidade: 0,
    grauComplexidade: 0,
    observacoes: ''
};

// Inicializar
document.addEventListener('DOMContentLoaded', function() {
    // Ativar primeiro step
    updateStepDisplay();
    
    // Atualizar custo de horas quando mudar
    const horasInput = document.getElementById('horas_analise');
    const valorHoraInput = document.getElementById('valor_hora_cobrado');
    
    if (horasInput) {
        horasInput.addEventListener('input', updateCustoHoras);
    }
    
    if (valorHoraInput) {
        valorHoraInput.addEventListener('input', updateCustoHoras);
    }
    
    updateCustoHoras();
    
    // Inicializar sliders
    ['urgencia', 'especificidade', 'complexidade'].forEach(type => {
        const slider = document.getElementById(type);
        if (slider) {
            updateSlider(type);
        }
    });
    
    // Atualizar preview quando mudar valor
    updatePreview();
});

// Navegação entre steps
function nextStep() {
    if (validateCurrentStep()) {
        if (calculatorData.step < 4) {
            // Salvar dados do step atual
            saveStepData();
            
            // Avançar step
            calculatorData.step++;
            updateStepDisplay();
            
            // Atualizar resumo se for o último step
            if (calculatorData.step === 4) {
                updateSummary();
            }
        }
    }
}

function prevStep() {
    if (calculatorData.step > 1) {
        calculatorData.step--;
        updateStepDisplay();
    }
}

function validateCurrentStep() {
    if (calculatorData.step === 1) {
        const nomeCliente = document.getElementById('nome_cliente').value.trim();
        const tipoServico = document.querySelector('input[name="tipo_servico"]:checked');
        
        if (!nomeCliente) {
            alert('Por favor, preencha o nome do cliente.');
            document.getElementById('nome_cliente').focus();
            return false;
        }
        
        if (!tipoServico) {
            alert('Por favor, selecione o tipo de serviço.');
            return false;
        }
        
        return true;
    }
    
    if (calculatorData.step === 2) {
        const valorHora = parseFloat(document.getElementById('valor_hora_cobrado').value);
        const horasAnalise = parseFloat(document.getElementById('horas_analise').value);
        
        if (!valorHora || valorHora <= 0) {
            alert('Por favor, preencha um valor/hora válido maior que zero.');
            document.getElementById('valor_hora_cobrado').focus();
            return false;
        }
        
        if (!horasAnalise || horasAnalise <= 0) {
            alert('Por favor, preencha as horas de análise com um valor maior que zero.');
            document.getElementById('horas_analise').focus();
            return false;
        }
        
        return true;
    }
    
    return true;
}

function saveStepData() {
    if (calculatorData.step === 1) {
        calculatorData.nomeCliente = document.getElementById('nome_cliente').value.trim();
        calculatorData.telefoneCliente = document.getElementById('telefone_cliente').value.trim();
        const tipoServico = document.querySelector('input[name="tipo_servico"]:checked');
        calculatorData.tipoServico = tipoServico ? tipoServico.value : 'Avaliação Psicológica';
    }
    
    if (calculatorData.step === 2) {
        calculatorData.valorHoraCobrado = parseFloat(document.getElementById('valor_hora_cobrado').value) || 100;
        calculatorData.horasAnalise = parseFloat(document.getElementById('horas_analise').value) || 10;
        updateCustoHoras();
    }
    
    if (calculatorData.step === 3) {
        calculatorData.grauUrgencia = parseInt(document.getElementById('urgencia').value) || 0;
        calculatorData.grauEspecificidade = parseInt(document.getElementById('especificidade').value) || 0;
        calculatorData.grauComplexidade = parseInt(document.getElementById('complexidade').value) || 0;
    }
}

function updateStepDisplay() {
    // Atualizar indicadores de step
    document.querySelectorAll('.step').forEach((step, index) => {
        const stepNumber = index + 1;
        step.classList.remove('active', 'completed');
        
        if (stepNumber < calculatorData.step) {
            step.classList.add('completed');
        } else if (stepNumber === calculatorData.step) {
            step.classList.add('active');
        }
    });
    
    // Atualizar cards visíveis
    document.querySelectorAll('.calc-card').forEach((card, index) => {
        card.classList.remove('active');
        if (index + 1 === calculatorData.step) {
            card.classList.add('active');
        }
    });
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Atualizar sliders
function updateSlider(type) {
    const slider = document.getElementById(type);
    const value = parseInt(slider.value);
    document.getElementById(type + 'Label').textContent = `+${value}%`;
    
    // Atualizar gradiente do slider
    const percent = (value / parseInt(slider.max)) * 100;
    slider.style.background = `linear-gradient(to right, #059669 0%, #059669 ${percent}%, #e5e7eb ${percent}%, #e5e7eb 100%)`;
    
    // Atualizar preview
    updatePreview();
}

// Atualizar preview de ajustes
function updatePreview() {
    // Preview não precisa de valor base, apenas mostra os ajustes percentuais
    const urgencia = parseInt(document.getElementById('urgencia')?.value || 0);
    const especificidade = parseInt(document.getElementById('especificidade')?.value || 0);
    const complexidade = parseInt(document.getElementById('complexidade')?.value || 0);
    
    const percentualTotal = urgencia + especificidade + complexidade;
    
    const previewAjustes = document.getElementById('previewAjustes');
    if (previewAjustes) previewAjustes.textContent = `+${percentualTotal}%`;
}

// Atualizar custo de horas
function updateCustoHoras() {
    const valorHoraCobrado = parseFloat(document.getElementById('valor_hora_cobrado')?.value || 100);
    const horas = parseFloat(document.getElementById('horas_analise')?.value || 10);
    
    // Sugestão: custo + 400% de margem (5x o custo)
    const sugestao = calculatorData.taxaHoraria * 5;
    
    const valorTotal = valorHoraCobrado * horas;
    const custoTotal = calculatorData.taxaHoraria * horas;
    const lucro = valorTotal - custoTotal;
    
    const sugestaoEl = document.getElementById('sugestaoValor');
    const horasDisplayEl = document.getElementById('horasDisplay');
    const valorTotalEl = document.getElementById('valorTotalHoras');
    const lucroEl = document.getElementById('lucroLiquido');
    
    if (sugestaoEl) sugestaoEl.textContent = `R$ ${sugestao.toFixed(2).replace('.', ',')}/h`;
    if (horasDisplayEl) horasDisplayEl.textContent = `${horas}h`;
    if (valorTotalEl) valorTotalEl.textContent = `R$ ${valorTotal.toFixed(2).replace('.', ',')}`;
    if (lucroEl) lucroEl.textContent = `R$ ${lucro.toFixed(2).replace('.', ',')}`;
}

// Atualizar resumo final
function updateSummary() {
    saveStepData();
    
    const valorHoraCobrado = calculatorData.valorHoraCobrado;
    const horasAnalise = calculatorData.horasAnalise;
    const valorTotalHoras = valorHoraCobrado * horasAnalise;
    
    const percentualTotal = calculatorData.grauUrgencia + calculatorData.grauEspecificidade + calculatorData.grauComplexidade;
    const ajustePercentual = valorTotalHoras * (percentualTotal / 100);
    const valorTotal = valorTotalHoras + ajustePercentual;
    
    document.getElementById('finalCliente').textContent = calculatorData.nomeCliente;
    document.getElementById('finalServico').textContent = calculatorData.tipoServico;
    document.getElementById('finalBase').textContent = `${horasAnalise}h × R$ ${valorHoraCobrado.toFixed(2).replace('.', ',')}`;
    document.getElementById('finalHoras').textContent = `R$ ${valorTotalHoras.toFixed(2).replace('.', ',')}`;
    document.getElementById('finalCustoHoras').textContent = percentualTotal > 0 ? `+${percentualTotal}%` : 'Nenhum';
    document.getElementById('finalAjustes').textContent = `R$ ${ajustePercentual.toFixed(2).replace('.', ',')}`;
    document.getElementById('finalTotal').textContent = `R$ ${valorTotal.toFixed(2).replace('.', ',')}`;
}

// Finalizar orçamento
async function finalizarOrcamento() {
    saveStepData();
    
    calculatorData.observacoes = document.getElementById('observacoes').value.trim();
    
    const valorHoraCobrado = calculatorData.valorHoraCobrado;
    const horasAnalise = calculatorData.horasAnalise;
    const valorTotalHoras = valorHoraCobrado * horasAnalise;
    
    const percentualTotal = calculatorData.grauUrgencia + calculatorData.grauEspecificidade + calculatorData.grauComplexidade;
    const ajustePercentual = valorTotalHoras * (percentualTotal / 100);
    const valorTotal = valorTotalHoras + ajustePercentual;
    
    const ajustes = [];
    if (calculatorData.grauUrgencia > 0) {
        ajustes.push({
            tipo: 'Urgência',
            percentual: calculatorData.grauUrgencia,
            valor: valorTotalHoras * (calculatorData.grauUrgencia / 100)
        });
    }
    if (calculatorData.grauEspecificidade > 0) {
        ajustes.push({
            tipo: 'Especificidade',
            percentual: calculatorData.grauEspecificidade,
            valor: valorTotalHoras * (calculatorData.grauEspecificidade / 100)
        });
    }
    if (calculatorData.grauComplexidade > 0) {
        ajustes.push({
            tipo: 'Complexidade',
            percentual: calculatorData.grauComplexidade,
            valor: valorTotalHoras * (calculatorData.grauComplexidade / 100)
        });
    }
    
    const payload = {
        nome_cliente: calculatorData.nomeCliente,
        telefone_cliente: calculatorData.telefoneCliente,
        tipo_servico: calculatorData.tipoServico,
        valor_base: valorTotalHoras,
        horas_analise: horasAnalise,
        grau_urgencia: calculatorData.grauUrgencia,
        grau_especificidade: calculatorData.grauEspecificidade,
        grau_complexidade: calculatorData.grauComplexidade,
        ajustes: ajustes,
        valor_ajustado: valorTotal,
        taxa_horaria: valorHoraCobrado,
        custo_horas_analise: valorTotalHoras,
        subtotal_fixo: valorTotalHoras,
        valor_total: valorTotal,
        observacoes: calculatorData.observacoes,
        opcoes_pagamento: []
    };
    
    try {
        const response = await fetch('/api/salvar-orcamento', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Orçamento salvo com sucesso!\nNúmero: ${data.numero}`);
            window.location.href = '/historico';
        } else {
            alert('Erro ao salvar orçamento: ' + (data.error || 'Erro desconhecido'));
        }
    } catch (error) {
        alert('Erro ao salvar orçamento: ' + error.message);
    }
}
