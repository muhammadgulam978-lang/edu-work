@login_required
def generate_paper_view(request, blueprint_id):
    """Blueprint se paper generate karo — Question Bank ke approved questions se."""
    blueprint = get_object_or_404(PaperBlueprint, id=blueprint_id)

    if request.method == 'POST':
        paper_set  = request.POST.get('paper_set', 'SINGLE')
        section_id = request.POST.get('section_id')

        try:
            with transaction.atomic():
                paper = GeneratedPaper.objects.create(
                    blueprint=blueprint,
                    section_id=section_id if section_id else None,
                    paper_set=paper_set,
                    generated_by=request.user,
                    status='DRAFT',
                )

                # ── Question Bank se approved questions select karo ──
                selected_questions = generate_paper_from_blueprint(blueprint)
                paper.questions.set(selected_questions)

                # ── Approval stages create karo ──────────────────────
                for stage in ['TEACHER', 'COORDINATOR', 'ACADEMIC_HEAD', 'CONTROLLER']:
                    PaperApproval.objects.create(
                        paper=paper, stage=stage, status='PENDING'
                    )

                # ── Warnings dikhao (agar koi thi) ───────────────────
                generation_warnings = getattr(blueprint, '_generation_warnings', [])
                for w in generation_warnings:
                    messages.warning(request, w)

                messages.success(
                    request,
                    f"✅ Paper Set '{paper_set}' generate ho gaya! "
                    f"({len(selected_questions)} questions Question Bank se liye gaye). "
                    f"Ab approval workflow shuru hoga."
                )
                return redirect('paper_approval_detail', paper_id=paper.id)

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('exam_plan_detail', plan_id=blueprint.exam_plan.id)

        except Exception as e:
            messages.error(request, f"❌ Paper generation failed: {str(e)}")
            return redirect('exam_plan_detail', plan_id=blueprint.exam_plan.id)

    sections = Section.objects.filter(class_fk=blueprint.exam_plan.class_fk)

    # ── Preview: kitne approved questions available hain ─────
    from exam_system.models import QuestionBank
    bank = QuestionBank.objects.filter(
        subject=blueprint.subject,
        class_fk=blueprint.exam_plan.class_fk,
    ).first()

    bank_stats = None
    if bank:
        bank_stats = {
            'total':    bank.questions.count(),
            'approved': bank.questions.filter(human_approved=True).count(),
        }

    return render(request, 'exam_system/generate_paper.html', {
        'blueprint':   blueprint,
        'sections':    sections,
        'set_choices': GeneratedPaper.SET_CHOICES,
        'bank_stats':  bank_stats,   # template mein dikhao
    })
    
    
    