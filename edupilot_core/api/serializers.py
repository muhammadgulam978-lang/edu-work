# from rest_framework import serializers, status
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from ..models import Student, FeeVoucher

# # 1. Serializer (Corrected fields)
# class FeeVoucherSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = FeeVoucher
#         # 'net_amount' model mein exist karta hai, 'amount' nahi
#         fields = ['voucher_no', 'month', 'due_date', 'net_amount', 'status']

# class StudentDashboardSerializer(serializers.ModelSerializer):
#     current_fee = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Student
#         fields = ['full_name', 'admission_number', 'current_fee']

#     def get_current_fee(self, obj):
#         # 'student' field FeeVoucher mein define hai, so filter(student=obj) is correct
#         voucher = FeeVoucher.objects.filter(student=obj).order_by('-id').first()
#         if voucher:
#             return FeeVoucherSerializer(voucher).data
#         return None

# # 2. API Logic
# class StudentDashboardAPI(APIView):
#     def get(self, request):
#         # Yahan main pehla student utha raha hoon (Testing ke liye)
#         student = Student.objects.first() 
#         if not student:
#             return Response({"error": "No student found"}, status=status.HTTP_404_NOT_FOUND)
            
#         serializer = StudentDashboardSerializer(student)
#         return Response(serializer.data, status=status.HTTP_200_OK)
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from ..models import Student, FeeVoucher, FeePlanDetail

# 1. Serializers
class FeeVoucherSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeVoucher
        fields = ['voucher_no', 'month', 'due_date', 'net_amount', 'status']

class StudentDashboardSerializer(serializers.ModelSerializer):
    current_fee = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = ['full_name', 'admission_number', 'current_fee']

    def get_current_fee(self, obj):
        voucher = FeeVoucher.objects.filter(student=obj).order_by('-id').first()
        return FeeVoucherSerializer(voucher).data if voucher else None

# 2. Student API Logic
class StudentDashboardAPI(APIView):
    renderer_classes = [JSONRenderer]
    
    def get(self, request):
        student = Student.objects.first() 
        if not student:
            return Response({"error": "No student found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = StudentDashboardSerializer(student)
        return Response(serializer.data, status=status.HTTP_200_OK)

# 3. Parent API Logic (Fixed Logic)
class ParentDashboardAPI(APIView):
    renderer_classes = [JSONRenderer]
    
    def get(self, request):
        students = Student.objects.all()
        serializer = StudentDashboardSerializer(students, many=True)
        
        # FIX: FeePlanDetail se amount nikalna (FeePlan model mein amount nahi hota)
        total_outstanding = 0
        for s in students:
            # Check karte hain ke student ka assignment exist karta hai ya nahi
            if hasattr(s, 'fee_assignment'):
                plan = s.fee_assignment.fee_plan
                # FeePlanDetail se us plan ka total amount nikal rahe hain
                details = FeePlanDetail.objects.filter(fee_plan=plan)
                total_outstanding += sum([d.amount for d in details])
        
        data = {
            "parent_name": "Parent User", 
            "children": serializer.data,
            "total_outstanding": float(total_outstanding)
        }
        return Response(data, status=status.HTTP_200_OK)